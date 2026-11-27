"""Drill for the paid-run guard hook in .claude/hooks/guard_paid_run.py: which
shell commands it blocks and which it lets through. Command strings only - nothing
is run, no network, no credentials.

    python tests/drill_guard_paid_run.py
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
HOOK = REPO_ROOT / ".claude" / "hooks" / "guard_paid_run.py"
sys.path.insert(0, str(HOOK.parent))
sys.path.insert(0, str(REPO_ROOT / "tests"))

import guard_paid_run
from _drill import expect


def blocked(command, shell="sh"):
    return guard_paid_run.decision(command, shell) is not None


def drill_blocks_paid_scripts():
    print("1. a paid script started by python is blocked without the marker")
    ok = True
    for command in (
        "PYTHONIOENCODING=utf-8 python src/paid_script.py --job x",
        "cd src && python paid_script.py",
        "python3 D:\\work\\project\\src\\paid_script.py",
        "py -3 src/paid_script.py",
        "python -m src.paid_script",
        "python paid_estimate_script.py run --go",
        "git status; python src/paid_script.py",
        "python -u src/paid_script.py",
    ):
        ok &= expect(f"blocked: {command}", blocked(command))
    for command in (
        "bash -c 'python src/paid_script.py'",
        'sh -c "python src/paid_script.py"',
        "Start-Process python -ArgumentList src/paid_script.py",
        "uv run src/paid_script.py",
        "python - < src/paid_script.py",
    ):
        ok &= expect(f"fails closed, an unknown way to run it: {command}", blocked(command))
    return ok


def drill_lets_free_commands_through():
    print("2. free commands and mentions of a paid file pass")
    ok = True
    for command in (
        "python tests/run_drills.py",
        "python paid_estimate_script.py run",
        "python paid_estimate_script.py estimate --runs 1",
        "git add src/paid_script.py",
        "grep -n run_job src/paid_script.py",
        "cat src/paid_script.py | head",
        "python -m py_compile src/paid_script.py",
        "ruff check src/paid_script.py",
        "git log --oneline -3 -- src/paid_script.py",
        "git diff --stat HEAD~1 -- src/paid_script.py",
        "git show HEAD:src/paid_script.py | head -5",
        'git commit -m "fix src/paid_script.py"',
        "npm run build",
    ):
        ok &= expect(f"passes: {command}", not blocked(command))
    return ok


def drill_marker_lets_paid_run_through():
    print("3. PROJECT_PAID_OK=1 lets a paid run through, in bash and PowerShell form")
    ok = True
    for command in (
        "PROJECT_PAID_OK=1 PYTHONIOENCODING=utf-8 python paid_estimate_script.py run --go",
        "PROJECT_PAID_OK=1 python src/paid_script.py",
    ):
        ok &= expect(f"passes: {command}", not blocked(command))
    ok &= expect(
        "PowerShell form passes",
        not blocked("$env:PROJECT_PAID_OK='1'; python src/paid_script.py", "powershell"),
    )
    ok &= expect(
        "PROJECT_PAID_OK=0 is still blocked", blocked("PROJECT_PAID_OK=0 python src/paid_script.py")
    )
    return ok


def drill_estimate_only_without_go():
    print("4. a script that only prints an estimate without --go passes; a continued line")
    print("   cannot hide --go")
    ok = True
    ok &= expect("without --go: allowed", not blocked("python paid_estimate_script.py run --tag t"))
    ok &= expect(
        "--g (argparse prefix): blocked", blocked("python paid_estimate_script.py run --g")
    )
    for continued in (
        "python paid_estimate_script.py run --tag t \\\n --go",
        "python paid_estimate_script.py run --tag t `\r\n --go",
    ):
        ok &= expect("continued --go without the marker: blocked", blocked(continued))
    ok &= expect(
        "continued --go with the marker: allowed",
        not blocked("PROJECT_PAID_OK=1 python paid_estimate_script.py run --tag t \\\n --go"),
    )
    return ok


def drill_read_only_git_and_pipes():
    print("5. git names a paid file only in read-only shapes; a pipe into an interpreter is denied")
    ok = True
    for command in (
        "git -c alias.x='!python src/paid_script.py' x",
        "git diff HEAD -- src/paid_script.py | python",
        "cat src/paid_script.py | python",
        "echo src/paid_script.py | xargs python",
        "git show HEAD:src/paid_script.py | sh",
    ):
        ok &= expect(f"blocked: {command}", blocked(command))
    for command in (
        "cat src/paid_script.py | wc -l",
        "git show HEAD:src/paid_script.py | grep -n def",
        "git grep -n run_job -- src/paid_script.py",
    ):
        ok &= expect(f"passes: {command}", not blocked(command))
    return ok


def drill_hook_protocol():
    print("6. as Claude Code calls it: JSON on stdin, deny JSON out, silence to allow")
    ok = True

    def run(payload):
        done = subprocess.run(
            [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True
        )
        return done.returncode, done.stdout.strip()

    code, out = run(
        json.dumps({"tool_name": "Bash", "tool_input": {"command": "python src/paid_script.py"}})
    )
    decision = json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None
    ok &= expect(
        "paid command: exit 0 and permissionDecision deny", code == 0 and decision == "deny"
    )
    code, out = run(json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}}))
    ok &= expect("free command: exit 0 and no output", code == 0 and out == "")
    code, out = run("not json")
    ok &= expect(
        "unreadable input: exit 0 and no output, the call goes through", code == 0 and out == ""
    )
    original = guard_paid_run.decision

    def crash(command, shell="sh"):
        raise RuntimeError("broken hook")

    guard_paid_run.decision = crash
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            sys.stdin = io.StringIO(
                json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}})
            )
            code = guard_paid_run.main()
    finally:
        guard_paid_run.decision = original
        sys.stdin = sys.__stdin__
    out = captured.getvalue().strip()
    decision = json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None
    ok &= expect("a crash while deciding: exit 0 and deny", code == 0 and decision == "deny")
    ok &= expect("the deny names the hook to fix", "guard_paid_run.py" in out)
    return ok


def drill_git_help_blocked():
    print("7. git help opens the browser on Windows, so it is blocked; git itself passes")
    ok = True
    for command in (
        "git rebase --help",
        "git help rebase",
        "git.exe push --help",
        "PROJECT_PAID_OK=1 git rebase --help",
        "GIT_PAGER=cat git log --help",
        "git -C wt_A help rebase",
        "git --no-pager help",
        "/usr/bin/git help rebase",
        r'"C:\Program Files\Git\cmd\git.exe" rebase --help',
        "env X=1 git help log",
        "git commit -q -F - <<'EOF' && git rebase --help\nmsg\nEOF",
        "git rebase --help>/dev/null",
        "(git help log)",
        "echo $(git help log)",
        "echo `git help log`",
        "git log `\r\n--help",
        'git "help" log',
    ):
        ok &= expect(f"blocked: {command}", blocked(command))
    result = guard_paid_run.decision("git rebase --help")
    ok &= expect(
        "the deny says why: the browser",
        result is not None and result[0] == "deny" and "browser" in result[1],
    )
    for command in (
        "git rebase -q origin/main && git log -1",
        "git rebase -h",
        "grep -n help docs/README.md",
        "python tests/run_drills.py --help",
        "git -C wt_A log --oneline -1",
        "(git status)",
        'git commit -m "see (git help x) in the notes"',
        "git commit -q -F - <<'EOF'\ngit help and git x --help are now denied\nEOF",
        'git commit -m "fix; git help x"',
    ):
        ok &= expect(f"passes: {command}", not blocked(command))
    return ok


def drill_git_push_blocked():
    print("8. a plain git push is blocked, the push pipeline ship.py passes")
    ok = True
    for command in (
        "git push",
        "git rebase -q origin/main && git push -q origin HEAD:main",
        'cd "C:/x/wt_A" && git -C wt_A push https://example.com/owner/project.git HEAD:main',
    ):
        ok &= expect(f"blocked: {command}", blocked(command))
    result = guard_paid_run.decision("git push")
    ok &= expect(
        "the reason names ship.py as a background job",
        result is not None
        and "python .claude/hooks/ship.py" in result[1]
        and "background" in result[1],
    )
    for command in (
        "python .claude/hooks/ship.py",
        'cd "C:/x/wt_A" && python .claude/hooks/ship.py --intent "push the fix"',
        'git commit -m "the guard denies git push now"',
        "git log --format=%s origin/main..HEAD",
    ):
        ok &= expect(f"passes: {command}", not blocked(command))
    return ok


def drill_bare_git_stash_blocked():
    print("9. a git stash without a pathspec is blocked, one with paths passes")
    ok = True
    for command in (
        "git stash",
        "git stash push",
        "git stash -u",
        "git stash save wip",
        "git -C wt stash push -m wip",
    ):
        ok &= expect(f"blocked: {command}", blocked(command))
    for command in (
        "git stash push -- src/a.py",
        "git stash list",
        "git stash show -p",
        "git stash pop",
        "git stash apply",
        "git stash drop",
    ):
        ok &= expect(f"passes: {command}", not blocked(command))
    return ok


def drill_private_search_blocked():
    print("10. a recursive search that can reach a protected folder is blocked, inside the repo")
    print("    only: the same folder names outside the repo are never touched")
    ok = True
    here = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        for command in (
            "grep -r token private_data",
            "grep -rn token private_data/sub",
            "grep -r token .",
            "grep -r token",
            "grep -rn token ./private_data/x.txt",
            "grep token private_data/*.json",
            "rg token private_data",
            "rg --no-ignore token src",
            "rg -g '*.json' token src",
            "findstr /s token private_data\\*",
            "Get-ChildItem -Recurse private_data | Select-String token",
            "Get-ChildItem -Recurse | Select-String token",
        ):
            ok &= expect(f"blocked: {command}", blocked(command))
        outside = tempfile.gettempdir().replace("\\", "/")
        for command in (
            "ls -R ~/.claude/skills",
            "grep -r token ~/.claude/skills",
            "grep -rn token " + outside,
            "grep -r token " + outside + "/private_data",
            "rg token " + outside + "/private_data",
            "Get-ChildItem -Recurse " + outside + " | Select-String token",
            "grep -rn token src --include=*.py",
            "grep -rn token src/app.py",
            "grep -c token private_data/one.json",
            "git grep -n token",
            "rg token src",
        ):
            ok &= expect(f"passes: {command}", not blocked(command))
    finally:
        os.chdir(here)
    return ok


if __name__ == "__main__":
    results = [
        drill_blocks_paid_scripts(),
        drill_lets_free_commands_through(),
        drill_marker_lets_paid_run_through(),
        drill_estimate_only_without_go(),
        drill_read_only_git_and_pipes(),
        drill_hook_protocol(),
        drill_git_help_blocked(),
        drill_git_push_blocked(),
        drill_bare_git_stash_blocked(),
        drill_private_search_blocked(),
    ]
    sys.exit(0 if all(results) else 1)
