"""Drill for the after-compaction hook in .claude/hooks/after_compact.py: what it
re-injects after a compaction and that it never blocks a session start. Runs on a
throwaway git repo in a temp folder; no network, no credentials.

    python tests/drill_after_compact.py

Cost: free - offline, invented files only.

Adapt per repo: nothing, as long as the hook keeps its COORDINATION, TAIL_LINES and
GIT_TIMEOUT names; drill 6 reads the hook timeout from .claude/settings.json. Needs
tests/_drill.py.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "after_compact.py"
sys.path.insert(0, str(HOOK.parent))

import after_compact
from _drill import expect


def make_repo(root, lines):
    git = ["git", "-C", str(root)]
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(git + ["config", "user.email", "d@x"], check=True)
    subprocess.run(git + ["config", "user.name", "drill"], check=True)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    subprocess.run(git + ["add", "a.txt"], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "first commit of the drill repo"], check=True)
    (root / "dirty.txt").write_text("x\n", encoding="utf-8")
    coord = root / after_compact.COORDINATION
    coord.parent.mkdir(parents=True)
    coord.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_hook(payload, root, project_dir=None):
    env = {"CLAUDE_PROJECT_DIR": str(project_dir or root), "PATH": os.environ["PATH"]}
    if "SYSTEMROOT" in os.environ:
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30,
    )


def drill_context_holds_fresh_facts():
    print("1. the context carries the COORDINATION.md tail, the last commit and the dirty file")
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        lines = ["2026-10-20 (session-%02d) - entry %d." % (i, i) for i in range(1, 31)]
        lines.insert(len(lines) - 3, "")
        lines.insert(len(lines) - 1, "   ")
        make_repo(root, lines)
        context = after_compact.build_context(root)
        first_kept = 31 - after_compact.TAIL_LINES
        ok &= expect("newest COORDINATION entry present", "entry 30." in context)
        ok &= expect(
            "oldest entry inside the tail present although two blank lines sit in the tail",
            "entry %d." % first_kept in context,
        )
        ok &= expect(
            "entry just outside the tail absent", "entry %d." % (first_kept - 1) not in context
        )
        ok &= expect("last commit subject present", "first commit of the drill repo" in context)
        ok &= expect("untracked file in the status", "dirty.txt" in context)
        ok &= expect("gate reminder present", "still needs the gate" in context)
    return ok


def drill_worktree_reads_the_main_checkout():
    print("2. a session in a git worktree still gets the main checkout's COORDINATION.md")
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "main"
        root.mkdir()
        make_repo(root, ["2026-10-20 (session-x) - HOLD written in the main checkout"])
        wt = Path(tmp) / "wt"
        subprocess.run(
            ["git", "-C", str(root), "worktree", "add", "-q", "--detach", str(wt)], check=True
        )
        try:
            ok &= expect(
                "main_checkout of the worktree is the main folder",
                after_compact.main_checkout(wt).resolve() == root.resolve(),
            )
            context = after_compact.build_context(wt)
            ok &= expect(
                "HOLD line reaches the worktree session",
                "HOLD written in the main checkout" in context,
            )
            ok &= expect(
                "status is the worktree's own (clean, no dirty.txt)", "dirty.txt" not in context
            )
        finally:
            subprocess.run(
                ["git", "-C", str(root), "worktree", "remove", "--force", str(wt)], check=True
            )
    return ok


def drill_crash_becomes_a_note():
    print("3. a crash while building the context is printed as a note, never a silent exit")
    saved = after_compact.build_context
    saved_stdin = sys.stdin

    def boom(root):
        raise RuntimeError("drill")

    after_compact.build_context = boom
    sys.stdin = io.StringIO(json.dumps({"source": "compact", "cwd": "."}))
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            after_compact.main()
    finally:
        after_compact.build_context = saved
        sys.stdin = saved_stdin
    try:
        reply = json.loads(out.getvalue())
    except ValueError:
        reply = {}
    context = reply.get("hookSpecificOutput", {}).get("additionalContext", "")
    return expect(
        "note names the failed hook and the error class",
        "after_compact hook failed: RuntimeError" in context,
    )


def drill_git_budget_fits_the_hook_timeout():
    print("6. three git calls at GIT_TIMEOUT each end before the hook timeout in settings.json")
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    timeout = None
    for entry in settings["hooks"]["SessionStart"]:
        for hook in entry["hooks"]:
            if hook["command"].endswith('after_compact.py"'):
                timeout = hook["timeout"]
    ok = expect(
        "after_compact.py is wired as a SessionStart hook with a timeout", timeout is not None
    )
    ok &= expect(
        "3 * GIT_TIMEOUT (%s) < hook timeout (%s)" % (3 * after_compact.GIT_TIMEOUT, timeout),
        timeout is not None and 3 * after_compact.GIT_TIMEOUT < timeout,
    )
    return ok


def drill_missing_coordination_is_a_note():
    print("4. a folder without COORDINATION.md or git gives a note, not a crash")
    with tempfile.TemporaryDirectory() as tmp:
        context = after_compact.build_context(Path(tmp))
    ok = expect("missing COORDINATION.md named", "no COORDINATION.md" in context)
    ok &= expect(
        "git failure named, context still built",
        "git failed" in context and "Last commits" in context,
    )
    return ok


def drill_hook_protocol():
    print(
        "5. the hook answers a compact start with SessionStart context and stays silent otherwise"
    )
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_repo(root, ["2026-10-20 (session-x) - HOLD: shared checkout"])
        out = run_hook(
            {"hook_event_name": "SessionStart", "source": "compact", "cwd": str(root)}, root
        )
        ok &= expect("exit 0 on compact", out.returncode == 0)
        try:
            reply = json.loads(out.stdout)
        except ValueError:
            reply = {}
        spec = reply.get("hookSpecificOutput", {})
        ok &= expect("hookEventName is SessionStart", spec.get("hookEventName") == "SessionStart")
        ok &= expect(
            "additionalContext carries the HOLD line",
            "HOLD: shared checkout" in spec.get("additionalContext", ""),
        )
        out = run_hook(
            {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(root)}, root
        )
        ok &= expect(
            "startup: exit 0 and no output", out.returncode == 0 and out.stdout.strip() == ""
        )
        for text in ("not json", "null", "[]", '"compact"'):
            out = subprocess.run(
                [sys.executable, str(HOOK)], input=text, capture_output=True, text=True, timeout=30
            )
            ok &= expect(
                "input %r: exit 0 and no output" % text,
                out.returncode == 0 and out.stdout.strip() == "",
            )
    return ok


def drill_session_folder_wins_over_project_dir():
    print(
        "7. the event's cwd (a worktree) is read, not CLAUDE_PROJECT_DIR (the checkout it was opened on)"
    )
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "main"
        root.mkdir()
        make_repo(root, ["2026-10-20 (session-x) - HOLD written in the main checkout"])
        wt = Path(tmp) / "wt"
        subprocess.run(
            ["git", "-C", str(root), "worktree", "add", "-q", "--detach", str(wt)], check=True
        )
        (wt / "only_in_worktree.txt").write_text("w", encoding="utf-8")
        try:
            out = run_hook({"source": "compact", "cwd": str(wt)}, root=wt, project_dir=root)
            context = json.loads(out.stdout)["hookSpecificOutput"]["additionalContext"]
            ok &= expect("status comes from the worktree", "only_in_worktree.txt" in context)
            ok &= expect("main checkout's dirty file absent", "dirty.txt" not in context)
            ok &= expect("the folder is named in the context", str(wt) in context)
            ok &= expect(
                "HOLD line still comes from the main checkout",
                "HOLD written in the main checkout" in context,
            )
        finally:
            subprocess.run(
                ["git", "-C", str(root), "worktree", "remove", "--force", str(wt)], check=True
            )
    return ok


if __name__ == "__main__":
    results = [
        drill_context_holds_fresh_facts(),
        drill_worktree_reads_the_main_checkout(),
        drill_crash_becomes_a_note(),
        drill_git_budget_fits_the_hook_timeout(),
        drill_missing_coordination_is_a_note(),
        drill_hook_protocol(),
        drill_session_folder_wins_over_project_dir(),
    ]
    sys.exit(0 if all(results) else 1)
