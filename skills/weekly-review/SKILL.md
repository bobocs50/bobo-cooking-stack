---
name: weekly-review
description: Interpret the weekly learning stats in ~/.claude/learning/weekly.md and update the user's learning profile. Run automatically when the SessionStart hook says a weekly review is due, or when the user says "weekly review" or invokes /weekly-review.
---

The user is learning to be a better engineer while agents write much of their code. Once a week this updates their learning record automatically; they read it when they want. Do not ask them questions: the update runs without them.

1. Read the newest entry in `~/.claude/learning/weekly.md` that says `Interpretation: pending`. If none is pending, run `python ~/.claude/learning/weekly_stats.py --force` first.
2. Read `~/.claude/learning/profile.md` (the user's loop, the concepts, how they read code, "Now"), `progress.md`, and the previous entries in `weekly.md`.
   If the user ran `/insights` since the last weekly entry, read the newest `~/.claude/usage-data/report-*.html` (by file date; never run `/insights` yourself) as extra evidence and name its date.
3. Write the interpretation in place of `Interpretation: pending`, 3–5 plain bullets, judged against the loop in `profile.md` only:
   - Which concept was introduced, studied, written as a `paper:` page and checked this week (find the pages in the transcripts). Is a redo due (~3 and ~10 days after a page)?
   - Which concept comes next, from "Now" in `profile.md`.
   - The code questions this week (see `learning-loop/CLAUDE.snippet.md`): how many were asked, how sure the user was against how right, and whether a risky diff went by without one.
   The "Background only" counts (corrections, done-when, subagents…) are context, never a target: do not praise or criticise a rise or drop in them.
4. Update `profile.md` only from evidence a check produced: a `paper:` page checked against the code or docs, a guess scored against real output, an answered code question, a test score. Never from keyword counts alone, and never from your own earlier verdicts. Date every change; move a concept between Strong / Developing / Revisit only with that evidence. Keep the user's own words.
5. If `profile.md` declares a freeze, respect it: do not propose new files, hooks, skills or rules until it ends.
6. If the week shows a lesson about working with Claude, add a dated line to `agentic-coding.md` under "Lessons learned".
7. Tell the user in two lines that the weekly review is done and where to read it, then continue with their request.

Never copy document content or long prompts into these files; counts and short quotes only.
