# Adapt per repo: set these before the first run; the rest of the file is production code as is.
#   COORDINATION  the gitignored coordination file of the repo (Shapes J); without one, point it at
#                 nothing and the context says "(no COORDINATION.md ...)".
#   TAIL_LINES    how many of its last non-blank lines go in (12).
#   GIT_TIMEOUT   seconds per git call; three calls must end inside the hook timeout set in
#                 .claude/settings.json (tests/drill_after_compact.py checks it).
#   the reminder  the closing line of build_context names the gates of this repo.
#   the register  cite the repo's own ids for the coordination log and the failure rule.
# Wire it as a SessionStart hook with matcher "compact" in .claude/settings.json.
"""SessionStart hook, matcher "compact": after every compaction, hands the new
context the facts a summary drops first, read fresh from disk: the tail of
.claude/orchestration/COORDINATION.md (what other sessions hold and run), the
last commits and the working-tree status of the folder the session runs in
(<D-id of the coordination log>, <D-id of the permanent-fix rule>).

Claude Code passes the event as JSON on stdin and reads the printed JSON back;
"additionalContext" is added to the compacted context. A session that runs in a
git worktree still gets the main checkout's COORDINATION.md: the file is
gitignored, so it lives beside the common git dir, not in the worktree.

Anything but a compact source or an unreadable input prints nothing; a failure
while building the context (git missing, a file unreadable, a crash) is printed
as a one-line note in the context instead, so the session learns the facts were
not re-read. Every path exits 0: the hook may never stop a session from starting.

Only coordination notes and git output are read, never the product's sensitive content.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

COORDINATION = Path(".claude") / "orchestration" / "COORDINATION.md"
TAIL_LINES = 12
LINE_CAP = 600
STATUS_LINES = 30
# Three git calls per run (status, rev-parse, log); their sum must stay under the
# hook timeout in .claude/settings.json, or a slow git kills the hook before it
# prints its note.
GIT_TIMEOUT = 4


def _git(root, args):
    try:
        out = subprocess.run(
            ["git", "-C", str(root)] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT,
        )
    except Exception as exc:
        return "(git failed: %s)" % exc.__class__.__name__
    if out.returncode != 0:
        return "(git failed: %s)" % out.stderr.strip()[:LINE_CAP]
    return out.stdout.rstrip()


def main_checkout(root):
    """The folder holding the gitignored orchestration notes: the parent of the
    common git dir, which is the main checkout even when root is a worktree."""
    common = _git(root, ["rev-parse", "--git-common-dir"])
    if common.startswith("(git failed"):
        return Path(root)
    return (Path(root) / common).resolve().parent


def coordination_tail(root):
    path = main_checkout(root) / COORDINATION
    if not path.is_file():
        return "(no COORDINATION.md in %s)" % path.parent
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return "(COORDINATION.md unreadable: %s)" % exc.__class__.__name__
    kept = []
    for line in lines:
        if line.strip():
            kept.append(line[:LINE_CAP])
    return "\n".join(kept[-TAIL_LINES:]) or "(COORDINATION.md is empty)"


def build_context(root):
    status = _git(root, ["status", "--short"]).splitlines()
    if len(status) > STATUS_LINES:
        status = status[:STATUS_LINES] + ["(... %d more)" % (len(status) - STATUS_LINES)]
    parts = [
        "Context was just compacted. Facts re-read from disk, newer than the summary:",
        "",
        "Last %d entries of COORDINATION.md (other sessions' holds and runs win over the summary):"
        % TAIL_LINES,
        coordination_tail(root),
        "",
        "Last commits of %s:" % root,
        _git(root, ["log", "--oneline", "-5"]),
        "",
        "Working tree of %s (git status --short):" % root,
        "\n".join(status) or "(clean)",
        "",
        "Before continuing: re-read the brief and the done-when line of the task in hand;"
        " a paid run, a commit or a push still needs the gate it needed before the compaction.",
    ]
    return "\n".join(parts)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(data, dict) or data.get("source") != "compact":
        return
    # The event's cwd is the folder the session works in, which may be a
    # worktree; CLAUDE_PROJECT_DIR stays on the checkout the session was opened on.
    root = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        context = build_context(root)
    except Exception as exc:
        context = "(after_compact hook failed: %s)" % exc.__class__.__name__
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                }
            }
        )
    )


if __name__ == "__main__":
    main()
