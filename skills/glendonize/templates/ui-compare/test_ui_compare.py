"""Free offline self-test for ui_compare.py: throwaway git repo, fake shots command, temp output root.

Cost: free. Run: python test_ui_compare.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "ui_compare.py")
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16

FAKE = """import os, sys
names = open("names.txt").read().split()
if "FAIL" in names:
    sys.exit(3)
out = os.environ["UI_COMPARE_OUT"]
assert os.environ["UI_PORT"].isdigit()
for n in names:
    open(os.path.join(out, n), "wb").write(%r)
""" % PNG

checks = 0


def expect(cond, label):
    global checks
    checks += 1
    if not cond:
        print("FAIL: " + label)
        sys.exit(1)
    print("ok: " + label)


def sh(*cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


def commit(repo, names, msg):
    with open(os.path.join(repo, "names.txt"), "w") as handle:
        handle.write(" ".join(names))
    sh("git", "add", "names.txt", cwd=repo)
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", msg, cwd=repo)
    return sh("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()


def main():
    tmp = tempfile.mkdtemp(prefix="uict")
    repo = os.path.join(tmp, "demo")
    root = os.path.join(tmp, "out")
    os.makedirs(repo)
    os.makedirs(root)
    env = dict(os.environ, UI_COMPARE_ROOT=root)
    try:
        sh("git", "init", "-q", cwd=repo)
        with open(os.path.join(repo, "fake_shots.py"), "w") as handle:
            handle.write(FAKE)
        cfg = {"cwd": ".", "setup": [], "shots": [sys.executable, "fake_shots.py"], "data": "invented"}
        with open(os.path.join(repo, ".ui-compare.json"), "w") as handle:
            json.dump(cfg, handle)
        sh("git", "add", "fake_shots.py", ".ui-compare.json", cwd=repo)
        base = commit(repo, ["a.png", "b.png"], "base")
        head = commit(repo, ["a.png", "c.png"], "head")

        def go(*extra, rev=head):
            return sh(
                sys.executable, SCRIPT, "--repo", repo, "--base", base, "--head", rev, *extra, env=env
            )

        res = go()
        last = res.stdout.strip().splitlines()[-1]
        expect(res.returncode == 0, "exit 0 on success")
        expect(last.startswith("UI_COMPARE ") and "FAILED" not in last, "last line is UI_COMPARE <path>")
        page = last[len("UI_COMPARE ") :]
        run_dir = os.path.dirname(page)
        expect(os.path.isabs(page) and os.path.exists(page), "compare.html path absolute and exists")
        expect(os.path.dirname(run_dir) == os.path.join(root, "demo"), "run folder under root/<repo-name>")
        expect(
            re.fullmatch(r"\d{4}-\d\d-\d\d-\d{4}-" + head[:8], os.path.basename(run_dir)) is not None,
            "folder name date-time-shortsha",
        )
        expect(os.path.exists(os.path.join(run_dir, ".ui-compare-run")), "marker file written")
        expect(sorted(os.listdir(os.path.join(run_dir, "before"))) == ["a.png", "b.png"], "before holds base shots")
        expect(sorted(os.listdir(os.path.join(run_dir, "after"))) == ["a.png", "c.png"], "after holds head shots")
        doc = open(page, encoding="utf-8").read()
        expect('src="before/a.png"' in doc and 'src="after/a.png"' in doc, "same-name row has both relative images")
        expect(
            '<span class="tag gone">gone</span>' in doc and 'src="before/b.png"' in doc,
            "base-only name shown as gone",
        )
        expect(
            '<span class="tag new">new</span>' in doc and 'src="after/c.png"' in doc,
            "head-only name shown as new",
        )
        expect("http://" not in doc and "https://" not in doc, "no http(s) URL in html")
        expect(head[:8] in doc and base[:8] in doc, "header names base and head commit")

        def worktrees_clean():
            listing = sh("git", "worktree", "list", cwd=repo).stdout.strip().splitlines()
            leftovers = [n for n in os.listdir(root) if n.startswith(".w")]
            return len(listing) == 1 and not leftovers

        expect(worktrees_clean(), "worktrees and temp folders removed after success")

        with open(os.path.join(repo, "names.txt"), "w") as handle:
            handle.write("a.png d.png")
        res = go(rev="WORKTREE")
        wt_page = res.stdout.strip().splitlines()[-1][len("UI_COMPARE ") :]
        expect(
            res.returncode == 0 and "d.png" in os.listdir(os.path.join(os.path.dirname(wt_page), "after")),
            "WORKTREE mode shots the uncommitted tree",
        )
        sh("git", "checkout", "--", "names.txt", cwd=repo)

        other = os.path.join(tmp, "other-wt")
        sh("git", "worktree", "add", "-q", "--detach", other, head, cwd=repo)
        res = sh(sys.executable, SCRIPT, "--repo", other, "--base", base, "--head", head, env=env)
        wt_last = res.stdout.strip().splitlines()[-1]
        expect(
            res.returncode == 0 and os.path.dirname(os.path.dirname(wt_last[len("UI_COMPARE ") :])) == os.path.join(root, "demo"),
            "run from a worktree lands under the main repo's name",
        )
        sh("git", "worktree", "remove", "--force", other, cwd=repo)

        before_dirs = sorted(os.listdir(os.path.join(root, "demo")))
        bad = commit(repo, ["FAIL"], "bad")
        res = go(rev=bad)
        expect(res.returncode == 1, "exit 1 when shots fail")
        expect(
            res.stdout.strip().splitlines()[-1].startswith("UI_COMPARE FAILED "),
            "last line UI_COMPARE FAILED <reason>",
        )
        expect(worktrees_clean(), "worktrees removed also when shots fail")
        expect(sorted(os.listdir(os.path.join(root, "demo"))) == before_dirs, "failed run leaves no partial run folder")

        res = sh(sys.executable, SCRIPT, "--repo", repo, env=env)
        expect(res.returncode == 2, "exit 2 on usage error")

        res = sh(sys.executable, SCRIPT, "--repo", repo, "--base", base, "--head", "nonexistent", env=env)
        expect(res.returncode == 1 and "UI_COMPARE FAILED" in res.stdout, "unknown commit fails with exit 1")

        nocfg = os.path.join(tmp, "nocfg")
        os.makedirs(nocfg)
        sh("git", "init", "-q", cwd=nocfg)
        with open(os.path.join(nocfg, "x.txt"), "w") as handle:
            handle.write("x")
        sh("git", "add", "x.txt", cwd=nocfg)
        sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c", cwd=nocfg)
        res = sh(sys.executable, SCRIPT, "--repo", nocfg, "--base", "HEAD", "--head", "HEAD", env=env)
        expect(
            res.returncode == 1 and ".ui-compare.json" in res.stdout and "needs one" in res.stdout.replace("skill needs one", "needs one"),
            "no config stops and names the need",
        )

        with open(os.path.join(nocfg, ".ui-compare.json"), "w") as handle:
            handle.write('{"shots": ["x"], "path_extra": ["C:\\Program Files\\nodejs"]}')
        sh("git", "add", ".ui-compare.json", cwd=nocfg)
        sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "bad", cwd=nocfg)
        res = sh(sys.executable, SCRIPT, "--repo", nocfg, "--base", "HEAD", "--head", "HEAD", env=env)
        expect(
            res.returncode == 1 and "UI_COMPARE FAILED" in res.stdout and "Traceback" not in res.stderr,
            "invalid config JSON fails cleanly with exit 1, no traceback",
        )

        repo_out = os.path.join(root, "demo")
        for name in os.listdir(repo_out):
            shutil.rmtree(os.path.join(repo_out, name))
        names = ["2020-01-%02d-0000-aaaa" % day for day in range(1, 13)]
        for name in names:
            os.makedirs(os.path.join(repo_out, name))
            open(os.path.join(repo_out, name, ".ui-compare-run"), "w").close()
        open(os.path.join(repo_out, names[0], "keep"), "w").close()
        nomarker = "2019-01-01-0000-nomarker"
        os.makedirs(os.path.join(repo_out, nomarker))
        flag = os.path.join(root, ".pruned-once")
        expect(not os.path.exists(flag), "no .pruned-once before first prune")

        res = sh(sys.executable, SCRIPT, "--repo", repo, "--prune-dry-run", env=env)
        expect(res.returncode == 0 and "would delete" in res.stdout, "--prune-dry-run prints what would go")
        expect(
            len(os.listdir(repo_out)) == 13 and not os.path.exists(flag),
            "--prune-dry-run deletes nothing, writes no flag",
        )

        res = go()
        expect(res.returncode == 0, "run with 12 old folders succeeds")
        expect(os.path.exists(flag), "first real prune writes .pruned-once")
        expect(
            all(os.path.isdir(os.path.join(repo_out, n)) for n in names),
            "first prune on the machine ran dry: nothing deleted",
        )
        expect("would delete" in res.stdout, "first prune printed its list")

        res = go()
        expect(res.returncode == 0, "second run succeeds")
        left = os.listdir(repo_out)
        expect(names[0] in left, "folder with keep file survives")
        expect(nomarker in left, "folder without marker survives")
        expect(names[1] not in left and names[2] not in left, "oldest marked folders pruned")
        marked = [n for n in left if n not in (names[0], nomarker)]
        expect(len(marked) == 11, "10 newest kept plus the new run (got %d)" % len(marked))
        print("all %d checks passed" % checks)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


main()
