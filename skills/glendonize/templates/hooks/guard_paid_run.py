"""PreToolUse hook: blocks a shell command that starts a paid script unless the
command carries PROJECT_PAID_OK=1, which Claude adds only after the user's go for
that run (D-074, AGENTS.md "Gates").

Claude Code passes the tool call as JSON on stdin. A blocked call gets a "deny"
decision with the reason; everything else exits 0 with no output, which lets the
call through. Unreadable input lets the call through too, so a broken hook
cannot stop every shell command.

Limit: it reads the command text. A script that imports a paid module and calls
it (a scratchpad probe importing main/step4_extraction.py) is not caught.
"""

import json
import re
import sys

PAID_SCRIPTS = (
    "step1_parsing",
    "pipeline",
    "api",
    "loop_run",
    "pn_run",
)

INTERPRETER = re.compile(r"(^|[\s\"'/\\])(python3?|py)(\.exe)?([\s\"']|$)", re.IGNORECASE)
SCRIPT = re.compile(r"(^|[\s\"'/\\])(" + "|".join(PAID_SCRIPTS) + r")\.py\b")
MARKER = re.compile(r"PROJECT_PAID_OK\s*=\s*[\"']?1")


def paid_script_in(command):
    """The paid script a command would start, or None."""
    for segment in re.split(r"&&|\|\||[;&|\n]", command):
        if not INTERPRETER.search(segment):
            continue
        if "py_compile" in segment:
            continue
        match = SCRIPT.search(segment)
        if match is None:
            continue
        name = match.group(2)
        # pn_run without --go only prints its estimate and spends nothing (AGENTS.md "Gates").
        if name == "pn_run" and "--go" not in segment:
            continue
        return name + ".py"
    return None


def decision(command):
    """'deny' with a reason, or None to let the command through."""
    script = paid_script_in(command)
    if script is None or MARKER.search(command):
        return None
    return (
        "deny",
        f"blocked: {script} costs money. Give the user the estimate and the "
        "remaining budget from notes/BUDGET.md and wait for their go; then rerun "
        "the command prefixed with PROJECT_PAID_OK=1 (D-074).",
    )


def main():
    try:
        call = json.load(sys.stdin)
        command = call["tool_input"]["command"]
    except Exception:
        return 0
    result = decision(command)
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
