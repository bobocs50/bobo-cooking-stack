"""ui-compare: before/after screenshots of a UI change, side by side in one HTML page.

Usage: python ui_compare.py --repo <path> --base <commit> --head <commit|WORKTREE> [--open] [--prune-dry-run]
Last stdout line: "UI_COMPARE <path of compare.html>" or "UI_COMPARE FAILED <reason>".
Exit codes: 0 success, 1 failure, 2 usage error. Python 3 stdlib only.
Env UI_COMPARE_ROOT overrides the output root (default ~/ui-compare), used by the self-test.
"""

import argparse
import datetime
import html
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import urllib.parse

CONFIG_NAME = ".ui-compare.json"
MARKER = ".ui-compare-run"
KEEP = "keep"
PRUNED_ONCE = ".pruned-once"
KEEP_NEWEST = 10
SHOTS_TIMEOUT = 900


class Fail(Exception):
    pass


def out_root():
    env = os.environ.get("UI_COMPARE_ROOT")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.expanduser("~"), "ui-compare")


def git(repo, *args):
    proc = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8"
    )
    if proc.returncode != 0:
        raise Fail("git " + " ".join(args) + ": " + proc.stderr.strip()[:300])
    return proc.stdout


def rmtree(path):
    def on_exc(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    if os.path.isdir(path):
        shutil.rmtree(path, onexc=on_exc)


def prune(repo_dir, dry_run):
    """Delete all but the newest KEEP_NEWEST marked run folders of one repo folder."""
    if not os.path.isdir(repo_dir):
        return
    candidates = []
    for name in sorted(os.listdir(repo_dir)):
        folder = os.path.join(repo_dir, name)
        if not os.path.isdir(folder):
            continue
        if not os.path.exists(os.path.join(folder, MARKER)):
            continue
        if os.path.exists(os.path.join(folder, KEEP)):
            continue
        candidates.append(folder)
    doomed = candidates[: max(0, len(candidates) - KEEP_NEWEST)]
    if not doomed:
        return
    flag = os.path.join(out_root(), PRUNED_ONCE)
    first_time = not os.path.exists(flag)
    if dry_run or first_time:
        for folder in doomed:
            print("ui-compare prune (dry, nothing deleted): would delete " + folder)
        if first_time and not dry_run:
            with open(flag, "w") as handle:
                handle.write("first prune ran dry\n")
        return
    for folder in doomed:
        print("ui-compare prune: deleting " + folder)
        rmtree(folder)


def read_config(checkout):
    path = os.path.join(checkout, CONFIG_NAME)
    if not os.path.exists(path):
        raise Fail(
            CONFIG_NAME
            + " missing in this repo: the skill needs one (see SKILL.md); "
            + "ask the user which test or invented data the screenshots may show"
        )
    try:
        with open(path, encoding="utf-8") as handle:
            cfg = json.load(handle)
    except (OSError, ValueError) as error:
        raise Fail(CONFIG_NAME + " unreadable: " + str(error)[:200])
    if not isinstance(cfg, dict) or "shots" not in cfg:
        raise Fail(CONFIG_NAME + " has no 'shots'")
    return cfg


def make_env(cfg, out_dir):
    env = dict(os.environ)
    extra = os.pathsep.join(cfg.get("path_extra", []))
    if extra:
        env["PATH"] = extra + os.pathsep + env.get("PATH", "")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    env["UI_PORT"] = str(sock.getsockname()[1])
    sock.close()
    env["UI_COMPARE_OUT"] = out_dir
    return env


def run_cmd(cmd, cwd, env, label, timeout=None):
    resolved = list(cmd)
    found = shutil.which(cmd[0], path=env.get("PATH"))
    if found:
        resolved[0] = found
    print("ui-compare: " + label + ": " + " ".join(cmd), flush=True)
    try:
        proc = subprocess.run(
            resolved,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise Fail(label + " timed out")
    except OSError as err:
        raise Fail(label + " could not start: " + str(err))
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-8:]
        raise Fail(label + " exited " + str(proc.returncode) + ": " + " | ".join(tail)[:600])


def copy_worktree(top, dest):
    raw = subprocess.run(
        ["git", "-C", top, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
    )
    if raw.returncode != 0:
        raise Fail("git ls-files failed")
    for rel in raw.stdout.decode("utf-8").split("\0"):
        if not rel:
            continue
        src = os.path.join(top, rel)
        if not os.path.isfile(src):
            continue
        target = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(src, target)


def add_checkout(top, rev, dest, created):
    if rev == "WORKTREE":
        os.makedirs(dest)
        created.append(("copy", dest))
        copy_worktree(top, dest)
    else:
        git(top, "worktree", "add", "--detach", dest, rev)
        created.append(("worktree", dest))


def remove_checkouts(top, created):
    for kind, dest in created:
        if kind == "worktree":
            subprocess.run(
                ["git", "-C", top, "worktree", "remove", "--force", dest], capture_output=True
            )
        rmtree(dest)
    subprocess.run(["git", "-C", top, "worktree", "prune"], capture_output=True)


def shots_in(folder):
    names = []
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith(".png"):
                names.append(name)
    return names


def build_html(repo_name, base_label, head_label, run_dir):
    before = shots_in(os.path.join(run_dir, "before"))
    after = shots_in(os.path.join(run_dir, "after"))
    names = sorted(set(before) | set(after))
    rows = []
    for name in names:
        quoted = urllib.parse.quote(name)
        if name in before and name in after:
            status = "same name"
        elif name in after:
            status = "new"
        else:
            status = "gone"
        left = "<em>none</em>"
        if name in before:
            left = '<img src="before/' + quoted + '" alt="before">'
        right = "<em>none</em>"
        if name in after:
            right = '<img src="after/' + quoted + '" alt="after">'
        rows.append(
            '<section class="row"><h2>'
            + html.escape(name)
            + ' <span class="tag '
            + status.replace(" ", "-")
            + '">'
            + status
            + "</span></h2>"
            + '<div class="pair"><div><h3>Before</h3>'
            + left
            + "</div><div><h3>After</h3>"
            + right
            + "</div></div></section>"
        )
    if not rows:
        rows.append("<p>No screenshots were written.</p>")
    css = (
        "body{font-family:system-ui,sans-serif;margin:16px;background:#fafafa;color:#111}"
        "h1{font-size:20px}.meta{color:#555;margin-bottom:16px}"
        ".row{margin-bottom:32px;border-top:1px solid #ccc;padding-top:8px}"
        ".row h2{font-size:16px}.pair{display:flex;gap:16px;align-items:flex-start}"
        ".pair>div{flex:1;min-width:0}.pair h3{font-size:13px;color:#555;margin:4px 0}"
        "img{max-width:100%;border:1px solid #ccc;background:#fff}"
        ".tag{font-size:12px;padding:1px 6px;border-radius:4px;background:#e5e5e5}"
        ".tag.new{background:#c8f0c8}.tag.gone{background:#f5c6c6}"
    )
    doc = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        + "<title>ui-compare "
        + html.escape(repo_name)
        + "</title><style>"
        + css
        + "</style></head><body>"
        + "<h1>ui-compare: "
        + html.escape(repo_name)
        + "</h1>"
        + '<div class="meta">Base '
        + html.escape(base_label)
        + " | Head "
        + html.escape(head_label)
        + "</div>"
        + "".join(rows)
        + "</body></html>"
    )
    path = os.path.join(run_dir, "compare.html")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(doc)
    return path


def repo_name_of(path):
    """The main checkout's folder name, the same from every worktree of the repo."""
    common = git(path, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    common = os.path.normpath(common)
    if os.path.basename(common) == ".git":
        return os.path.basename(os.path.dirname(common))
    return os.path.basename(git(path, "rev-parse", "--show-toplevel").strip())


def run(args):
    top = git(args.repo, "rev-parse", "--show-toplevel").strip()
    repo_name = repo_name_of(top)
    root = out_root()
    repo_dir = os.path.join(root, repo_name)
    os.makedirs(repo_dir, exist_ok=True)
    prune(repo_dir, False)
    base_sha = git(top, "rev-parse", "--short=8", "--verify", args.base + "^{commit}").strip()
    if args.head == "WORKTREE":
        head_sha = git(top, "rev-parse", "--short=8", "HEAD").strip()
        head_label = "WORKTREE (on " + head_sha + ")"
        sha_part = head_sha + "-wt"
    else:
        head_sha = git(top, "rev-parse", "--short=8", "--verify", args.head + "^{commit}").strip()
        head_label = head_sha
        sha_part = head_sha
    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    run_dir = os.path.join(repo_dir, stamp + "-" + sha_part)
    suffix = 1
    while os.path.exists(run_dir):
        suffix += 1
        run_dir = os.path.join(repo_dir, stamp + "-" + sha_part + "-" + str(suffix))
    os.makedirs(os.path.join(run_dir, "before"))
    os.makedirs(os.path.join(run_dir, "after"))
    tmp = tempfile.mkdtemp(prefix=".w", dir=root)
    created = []
    ok = False
    try:
        base_dir = os.path.join(tmp, "b")
        head_dir = os.path.join(tmp, "h")
        add_checkout(top, args.base, base_dir, created)
        add_checkout(top, args.head, head_dir, created)
        cfg = read_config(head_dir)
        sub = cfg.get("cwd", ".")
        for name in cfg.get("copy_into_base", []):
            src = os.path.join(head_dir, sub, name)
            dst = os.path.join(base_dir, sub, name)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        for side, checkout in (("before", base_dir), ("after", head_dir)):
            cwd = os.path.join(checkout, sub)
            env = make_env(cfg, os.path.join(run_dir, side))
            for step in cfg.get("setup", []):
                run_cmd(step, cwd, env, side + " setup")
            run_cmd(cfg["shots"], cwd, env, side + " shots", SHOTS_TIMEOUT)
        with open(os.path.join(run_dir, MARKER), "w") as handle:
            handle.write("ui-compare run\n")
        path = build_html(repo_name, base_sha, head_label, run_dir)
        ok = True
        return path
    finally:
        remove_checkouts(top, created)
        rmtree(tmp)
        if not ok:
            rmtree(run_dir)


def main():
    parser = argparse.ArgumentParser(description="Before/after UI screenshots")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--prune-dry-run", action="store_true")
    args = parser.parse_args()
    if not args.prune_dry_run and (not args.base or not args.head):
        parser.error("--base and --head are required")
    try:
        if args.prune_dry_run:
            top = git(args.repo, "rev-parse", "--show-toplevel").strip()
            prune(os.path.join(out_root(), repo_name_of(top)), True)
            return 0
        path = run(args)
    except Fail as err:
        print("UI_COMPARE FAILED " + str(err).replace("\n", " "))
        return 1
    if args.open and hasattr(os, "startfile"):
        os.startfile(path)
    print("UI_COMPARE " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
