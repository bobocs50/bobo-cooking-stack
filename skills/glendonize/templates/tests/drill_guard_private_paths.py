"""Drill for the protected-folder hook in .claude/hooks/guard_private_paths.py: which Read, Grep
and Glob calls it denies and which it lets through. Paths only - nothing is read, no network,
no credentials.

    python tests/drill_guard_private_paths.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "guard_private_paths.py"
sys.path.insert(0, str(HOOK.parent))
sys.path.insert(0, str(REPO_ROOT / "tests"))

import guard_private_paths
from _drill import expect

PROTECTED = guard_private_paths.PROTECTED_FOLDERS[0][0]


def denied(tool_input, tool_name="Read"):
    return guard_private_paths.decision(tool_input, tool_name) is not None


def drill_protected_folders_denied():
    print("1. a path inside a protected folder of this repo is denied")
    ok = True
    for tool_input in (
        {"file_path": PROTECTED + "/a.json"},
        {"file_path": "./" + PROTECTED + "/sub/b.txt"},
        {"file_path": str(REPO_ROOT / PROTECTED / "a.json")},
        {"file_path": str(REPO_ROOT / PROTECTED / "a.json").replace("\\", "/")},
        {"file_path": PROTECTED.upper() + "/A.JSON"},
        {"path": PROTECTED, "pattern": "token"},
        {"path": PROTECTED + "/sub", "glob": "*.json"},
        {"file_path": "src/../" + PROTECTED + "/a.json"},
    ):
        ok &= expect(f"denied: {tool_input}", denied(tool_input))
    ok &= expect(
        "denied: Glob pattern " + PROTECTED + "/**/*.json",
        denied({"pattern": PROTECTED + "/**/*.json"}, "Glob"),
    )
    return ok


def drill_outside_the_repo_passes():
    print("2. a path outside the repo is never denied, whatever its folders are called")
    ok = True
    outside = tempfile.gettempdir()
    for tool_input in (
        {"file_path": outside + "/" + PROTECTED + "/a.json"},
        {"path": "~/.claude/skills"},
        {"path": "~/.claude/skills/" + PROTECTED},
        {"file_path": str(Path.home() / ".claude" / "skills" / "x" / "SKILL.md")},
        {"path": outside, "pattern": "token"},
    ):
        ok &= expect(f"passes: {tool_input}", not denied(tool_input))
    return ok


def drill_code_and_other_folders_pass():
    print("3. the repo's own code and other folders stay readable")
    ok = True
    for tool_input in (
        {"file_path": str(REPO_ROOT / "AGENTS.md")},
        {"file_path": "src/app.py"},
        {"path": "tests", "pattern": "D-001"},
        {"file_path": PROTECTED + "_notes.md"},
        {},
    ):
        ok &= expect(f"passes: {tool_input}", not denied(tool_input))
    ok &= expect(
        "passes: Grep regex naming the folder is a code search, not a path",
        not denied({"pattern": PROTECTED + "/", "path": "src"}, "Grep"),
    )
    return ok


def drill_reaches_protected():
    print("4. reaches_protected (the shell guard's test) also flags a folder above one")
    ok = True
    here = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        reaches = guard_private_paths.reaches_protected
        ok &= expect("the repo root reaches it", reaches("."))
        ok &= expect("the folder itself reaches it", reaches(PROTECTED))
        ok &= expect("a wildcard folder name reaches it", reaches("*/*.json"))
        ok &= expect("src does not", not reaches("src"))
        ok &= expect("a temp folder outside the repo does not", not reaches(tempfile.gettempdir()))
        ok &= expect("~/.claude/skills does not", not reaches("~/.claude/skills"))
    finally:
        os.chdir(here)
    return ok


def drill_suffix_rule():
    print("5. PROTECTED_SUFFIXES denies an untracked file of that type inside the repo only")
    ok = True
    original = guard_private_paths.PROTECTED_SUFFIXES
    guard_private_paths.PROTECTED_SUFFIXES = (".pdf",)
    try:
        ok &= expect("untracked PDF in the repo: denied", denied({"file_path": "x/new-report.pdf"}))
        ok &= expect(
            "PDF outside the repo: passes",
            not denied({"file_path": tempfile.gettempdir() + "/report.pdf"}),
        )
        ok &= expect("a non-PDF passes", not denied({"file_path": "x/new-report.txt"}))
    finally:
        guard_private_paths.PROTECTED_SUFFIXES = original
    return ok


def drill_allowed_env():
    print("6. ALLOWED_ENV set to 1 turns the hook off; empty ALLOWED_ENV has no switch")
    ok = True
    original = guard_private_paths.ALLOWED_ENV
    guard_private_paths.ALLOWED_ENV = "DRILL_PRIVATE_OK"
    os.environ["DRILL_PRIVATE_OK"] = "1"
    try:
        ok &= expect("switch on: passes", not denied({"file_path": PROTECTED + "/a.json"}))
    finally:
        os.environ.pop("DRILL_PRIVATE_OK", None)
        guard_private_paths.ALLOWED_ENV = original
    ok &= expect("switch off: denied again", denied({"file_path": PROTECTED + "/a.json"}))
    return ok


def drill_hook_protocol():
    print("7. as Claude Code calls it: JSON on stdin, deny JSON out, silence to allow")
    ok = True

    def run(payload):
        done = subprocess.run(
            [sys.executable, str(HOOK)],
            input=payload,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        return done.returncode, done.stdout.strip()

    code, out = run(
        json.dumps({"tool_name": "Read", "tool_input": {"file_path": PROTECTED + "/a.json"}})
    )
    verdict = json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None
    ok &= expect("protected file: exit 0 and permissionDecision deny", code == 0 and verdict == "deny")
    ok &= expect("the reason starts with 'Private:'", '"Private: ' in out)
    code, out = run(json.dumps({"tool_name": "Read", "tool_input": {"file_path": "AGENTS.md"}}))
    ok &= expect("own file: exit 0 and no output", code == 0 and out == "")
    code, out = run("not json")
    ok &= expect("unreadable input: exit 0 and no output", code == 0 and out == "")
    return ok


def main():
    passed = drill_protected_folders_denied()
    passed &= drill_outside_the_repo_passes()
    passed &= drill_code_and_other_folders_pass()
    passed &= drill_reaches_protected()
    passed &= drill_suffix_rule()
    passed &= drill_allowed_env()
    passed &= drill_hook_protocol()
    print("ALL PASSED" if passed else "FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    os.chdir(REPO_ROOT)
    sys.exit(main())
