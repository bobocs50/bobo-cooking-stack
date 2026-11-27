"""PreToolUse hook for Read, Grep and Glob: denies a file tool call that would read a folder
this repo keeps private (customer data, proprietary documents, anything the rules say must not
reach this session), so the step goes to whoever may read it instead.

PROTECTED_FOLDERS lists them, relative to the repo root, as tuples of folder names. Only a path
that resolves INSIDE the repo and inside one of those folders is denied. A path outside the repo
(~/.claude/skills, a temp folder, another project) is never denied, whatever its folders are
called: an earlier version matched folder names anywhere in a path and blocked `ls -R` and
`grep` on a skills folder (seen 2026-11-26). Symlinks and junctions are followed by realpath, so
a link inside the repo that points to a protected folder is caught; a link outside it is not.

A Grep's `pattern` is the regex searched for, not a path, so only a Glob's `pattern` is checked.
PROTECTED_SUFFIXES (default none) also denies an untracked file of that type inside the repo
(e.g. ".pdf" for report files); a file git tracks passes. ALLOWED_ENV names an environment
variable whose value "1" turns the hook off, for the one tool that is cleared to read these
folders (leave it empty to have none).

The shell side, a recursive search over those folders, stays with guard_paid_run.py, which
imports reaches_protected from here. Unreadable input passes, and a crash in the decision denies.
"""

import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PATH_KEYS = ("file_path", "path", "notebook_path", "glob")
PROTECTED_FOLDERS = (("private_data",),)
PROTECTED_SUFFIXES = ()
ALLOWED_ENV = ""
WILDCARDS = ("*", "?", "[")


def repo_parts(path):
    """The lower-cased folder names of `path` below the repo root, or None when it is outside."""
    expanded = os.path.expanduser(path)
    joined = os.path.join(os.getcwd(), expanded)
    try:
        resolved = os.path.realpath(joined)
    except (OSError, ValueError):
        resolved = os.path.abspath(joined)
    root = os.path.realpath(str(REPO_ROOT))
    try:
        relative = os.path.relpath(resolved, root)
    except ValueError:
        return None
    parts = []
    for part in relative.replace("\\", "/").split("/"):
        if part not in ("", "."):
            parts.append(part.lower())
    if parts and parts[0] == "..":
        return None
    return parts


def part_matches(part, name):
    return fnmatch.fnmatch(part, name.lower()) or fnmatch.fnmatch(name.lower(), part)


def inside_protected(path):
    parts = repo_parts(path)
    if parts is None:
        return False
    for folder in PROTECTED_FOLDERS:
        if len(parts) < len(folder):
            continue
        matched = True
        for index, name in enumerate(folder):
            if not part_matches(parts[index], name):
                matched = False
        if matched:
            return True
    return False


def reaches_protected(path):
    """True when a search that walks `path` recursively would read a protected folder: the path
    is inside one, or is a folder above one (the repo root, a parent)."""
    parts = repo_parts(path)
    if parts is None:
        return False
    for folder in PROTECTED_FOLDERS:
        shared = min(len(parts), len(folder))
        matched = True
        for index in range(shared):
            if not part_matches(parts[index], folder[index]):
                matched = False
        if matched:
            return True
    return False


def tracked(path):
    for wildcard in WILDCARDS:
        if wildcard in path:
            return False
    if repo_parts(path) is None:
        return False
    done = subprocess.run(
        [
            "git",
            "--literal-pathspecs",
            "-C",
            str(REPO_ROOT),
            "ls-files",
            "--error-unmatch",
            os.path.join(os.getcwd(), os.path.expanduser(path)),
        ],
        capture_output=True,
        text=True,
    )
    return done.returncode == 0


def is_private(path):
    if inside_protected(path):
        return True
    if PROTECTED_SUFFIXES and path.lower().endswith(PROTECTED_SUFFIXES):
        if repo_parts(path) is not None and not tracked(path):
            return True
    return False


def decision(tool_input, tool_name=""):
    if ALLOWED_ENV and os.environ.get(ALLOWED_ENV) == "1":
        return None
    keys = PATH_KEYS
    if tool_name == "Glob":
        keys = PATH_KEYS + ("pattern",)
    for key in keys:
        value = tool_input.get(key)
        if isinstance(value, str) and value and is_private(value):
            return (
                "deny",
                f"Private: `{value}` is in a folder this repo keeps out of this session "
                "(PROTECTED_FOLDERS in .claude/hooks/guard_private_paths.py). Stop this step, "
                "tell the user in one message starting with 'Private:' what to check and what "
                "answer you need back, and go on with the work that does not depend on it.",
            )
    return None


def main():
    try:
        call = json.load(sys.stdin)
        tool_input = call["tool_input"]
        tool_name = call.get("tool_name") or ""
    except Exception:
        return 0
    try:
        result = decision(tool_input, tool_name)
    except Exception as error:
        result = (
            "deny",
            f"Private: the protected-folder hook failed while deciding ({error!r}); fix "
            ".claude/hooks/guard_private_paths.py before reading this path.",
        )
    if result is None:
        return 0
    verdict, reason = result
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": verdict,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
