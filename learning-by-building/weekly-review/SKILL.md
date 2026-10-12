---
name: weekly-review
description: Interpret the weekly learning stats in ~/.claude/learning/weekly.md and update the user's learning profile. Run automatically when the SessionStart hook says a weekly review is due, or when the user says "weekly review" or invokes /weekly-review.
---

The user is a 4th-semester Information Systems student aiming for a software / AI engineering internship, and has no software-engineer supervisor. Once a week this updates their learning record automatically; they read it when they want. Do not ask them questions: the update runs without them.

1. Read the newest entry in `~/.claude/learning/weekly.md` that says `Interpretation: pending`. If none is pending, run `python ~/.claude/learning/weekly_stats.py --force` first.
2. Read `~/.claude/learning/profile.md` ("How learning works here", "How the user reads code", "Monthly check", "Now"), `progress.md` ("Records", "Needs reinforcement", "Words you used"), and the previous entries in `weekly.md`.
   If the user ran `/insights` since the last weekly entry, read the newest `~/.claude/usage-data/report-*.html` (by file date; never run `/insights` yourself) as extra evidence and name its date.
3. Write the interpretation in place of `Interpretation: pending`, 3–5 plain bullets, judged against the loop in `profile.md` ("How learning works here") only:
   - Was a concept introduced this week with a source and an "after this you can:" line (loop step 1)? Did reading follow a wrong rating (step 4)?
   - The code-question line: asked, answered, with sure/unsure said. Which records were added to `progress.md` this week, and what each says the user can do now. Is a redo of the same kind of check due (~3 and ~10 days after a record)?
   - Was a prediction written before a paid run this week, and did the run confirm it (the run's findings in `notes/`)?
   - Which concept comes next, from "Now" in `profile.md`.
   - Prompt diffs in `main/` this week: were they shown to the user before the run (D-085)?
   The "Background only" counts (corrections, done-when, subagents…) are context, never a target: do not praise or criticise a rise or drop in them.
4. Update `profile.md` only from evidence a check produced: a code question rated, a pre-run prediction scored against the run, a monthly test score. Never from keyword counts alone, and never from your own earlier verdicts. Date every change; move a concept between Strong / Developing / Revisit only with that evidence. Keep the user's own words.
5. Do not propose new files, hooks, skills or rules; the user builds those when they ask for them.
6. If the week shows a lesson about working with Claude, add a dated line to `agentic-coding.md` under "Lessons learned".
7. Tell the user in two lines that the weekly review is done and where to read it, then continue with their request.

**Headless run (the Monday task gives you Read, Glob and Grep only, no Edit):** do not try to edit. End your output with the interpretation bullets between a line `<<<INTERPRETATION` and a line `INTERPRETATION>>>`, and the exact profile.md / agentic-coding.md changes you would have made between `<<<PROFILE` and `PROFILE>>>` (file, section, the line to add). `run_weekly.ps1` writes the first block into weekly.md and marks the second as pending; the next interactive session applies it.

Never copy document content or long prompts into these files; counts and short quotes only.
