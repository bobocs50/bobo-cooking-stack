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

Closing is the user's practice moment for evals and code review (`~/.claude/learning/profile.md`, current focus). Before proposing the close (CLAUDE.md "Approval before acting"), walk these four steps and wait at each one:

1. Show the latest eval numbers against the target, with the run and its date (CLAUDE.md "Definition of done for issues"). If there is no fresh run, say so.
2. Ask the user to explain the numbers back in 2–3 sentences: what moved, what is left. Ask in plain text, then wait. Correct only what is wrong; don't explain it for them first.
3. The diff, by phase (`~/.claude/learning/profile.md`, "Code reading by phase"). While the architecture is still being experimented with: show only the one diff that holds the fix and ask "does this do what the issue wanted?", then trace 3 extracted values by hand to the cited page. Once the architecture is settled: walk through the whole diff a few lines at a time. In both phases, ask the user to name one thing that could go wrong, and whether a drill would catch it ("would this drill fail if the fix were wrong?").
4. Only then propose the close, and close it on the user's go.

The user can say "skip" at any step. Then record it as skipped, not practised.
