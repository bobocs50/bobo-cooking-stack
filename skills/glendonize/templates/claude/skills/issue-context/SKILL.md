---
name: issue-context
description: Load full context for a GitHub issue of this repo. Use when the user says "pull issue N", "reload context on issue N", "where are we on #N", or invokes /issue-context N.
---

Read-only. Costs nothing: no paid script runs here (AGENTS.md "Gates").

1. `gh issue view $ARGUMENTS --comments`
2. Read the decisions (D-xxx) and open questions (Q-xxx) the issue names, in `notes/DECISIONS.md` and `notes/OPEN_QUESTIONS.md`. Also grep both files for `#$ARGUMENTS` to find ones the issue doesn't name.
3. Find the latest eval result for this issue's metric: the newest scored run in the issue comments, and the matching folder under `eval/out/`. Say which run and date the numbers come from. If none is newer than the last change to `main/` for this issue, say so (CLAUDE.md "Definition of done for issues").
4. Check `.claude/orchestration/COORDINATION.md` for anything in flight or waiting on the user for this issue.
5. Output, in plain language, 10 bullets max: goal, current metric vs target (with numbers), open questions, what waits on the user, next step.
6. Do NOT change anything. Wait for the user's instruction.

## When the user wants to close the issue

1. Show the latest eval numbers against the target, with the run and its date (CLAUDE.md "Definition of done for issues"). If there is no fresh run, say so.
2. Then propose the close, and close it on the user's go (CLAUDE.md "Approval before acting").
