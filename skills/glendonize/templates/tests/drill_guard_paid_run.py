"""Drill for the paid-run guard hook in .claude/hooks/guard_paid_run.py: which
shell commands it blocks and which it lets through (D-074). Command strings
only - nothing is run, no network, no credentials.

    python tests/drill_guard_paid_run.py
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "guard_paid_run.py"
sys.path.insert(0, str(HOOK.parent))

import guard_paid_run
from _drill import expect


def blocked(command):
    return guard_paid_run.decision(command) is not None


def drill_blocks_paid_scripts():
    print("1. a paid script started by python is blocked without the marker")
    ok = True
    for command in (
        "PYTHONIOENCODING=utf-8 python main/pipeline.py --dossier x",
        "cd main && python pipeline.py",
        "python main/api.py",
        "python main/step1_parsing.py",
        "python eval/loop_run.py",
        "python eval/pn_run.py run --tag t --go",
        "python3 D:\\work\\project\\eval\\pn_run.py layer2 --go",
        "git status; python main/api.py",
        "python eval/pn_run.py run --go",
    ):
        ok &= expect(f"blocked: {command}", blocked(command))
    return ok


def drill_lets_free_commands_through():
    print("2. free commands and mentions of a paid file pass")
    ok = True
    for command in (
        "python tests/run_drills.py",
        "python eval/pn_run.py run --tag t",
        'PYTHONIOENCODING=utf-8 python eval/pn_run.py estimate --tag d113 --runs 1 --root "C:/x y/corpus-c"',
        "python eval/pn_report.py --tag t",
        "git add main/pipeline.py",
        "grep -n run_dossier main/pipeline.py",
        "cat main/api.py | head",
        "python -m py_compile main/api.py",
        "npm run build",
    ):
        ok &= expect(f"passes: {command}", not blocked(command))
    return ok


def drill_marker_lets_paid_run_through():
    print("3. PROJECT_PAID_OK=1 lets a paid run through, in bash and PowerShell form")
    ok = True
    for command in (
        "PROJECT_PAID_OK=1 PYTHONIOENCODING=utf-8 python eval/pn_run.py run --tag t --go",
        "$env:PROJECT_PAID_OK='1'; python main/pipeline.py",
    ):
        ok &= expect(f"passes: {command}", not blocked(command))
    ok &= expect("PROJECT_PAID_OK=0 is still blocked", blocked("PROJECT_PAID_OK=0 python main/api.py"))
    return ok


def drill_hook_protocol():
    print("4. as Claude Code calls it: JSON on stdin, deny JSON out, silence to allow")
    ok = True

    def run(payload):
        done = subprocess.run(
            [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True
        )
        return done.returncode, done.stdout.strip()

    code, out = run(
        json.dumps({"tool_name": "Bash", "tool_input": {"command": "python main/api.py"}})
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
    return ok


if __name__ == "__main__":
    results = [
        drill_blocks_paid_scripts(),
        drill_lets_free_commands_through(),
        drill_marker_lets_paid_run_through(),
        drill_hook_protocol(),
    ]
    sys.exit(0 if all(results) else 1)
