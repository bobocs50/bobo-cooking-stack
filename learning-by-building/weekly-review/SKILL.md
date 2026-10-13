---
name: weekly-review
description: Interpret the weekly learning stats in ~/.claude/learning/weekly.md and update the user's learning profile. Run automatically when the SessionStart hook says a weekly review is due, or when the user says "weekly review" or invokes /weekly-review.
---

The user is learning to be an engineer while agents write most of the code, with no senior engineer looking over the work. Once a week this updates their learning record automatically; they read it when they want. Do not ask them questions: the update runs without them.

1. Read the newest entry in `~/.claude/learning/weekly.md` that says `Interpretation: pending`. If none is pending, run `python ~/.claude/learning/weekly_stats.py --force` first.
2. Read `~/.claude/learning/profile.md` ("How learning works here", "How the user reads code", "Monthly check", "Now"), `progress.md` ("Records", "Needs reinforcement", "Words you used", "Terms"), and the previous entries in `weekly.md`.
   If the user ran `/insights` since the last weekly entry, read the newest `~/.claude/usage-data/report-*.html` (by file date; never run `/insights` yourself) as extra evidence and name its date.
3. Write the interpretation in place of `Interpretation: pending` as **six bullets with these exact bold labels, in this order** (the user, 2026-10-12: "it should show me how good I got, how I progressed, what I did not good, what I learned, what I should learn"). Writing rule for every bullet: 2–4 lines, one sentence per line, each sentence at most 12 words, continuation lines indented two spaces under the bullet; plain words a student reads in ten seconds, addressed to the user as "you"; a number always stands next to last week's number ("18 corrections, 21 last week"); no file names, no decision ids, no quotes longer than six words. Example bullet in that shape (copy the shape, not the words):
   - **How you got better:** You answered two code questions, none last week.
     Both times you found the deciding line yourself.
     One needed a hint; one was right for the wrong reason.
   The six bullets:
   - `**How you got better:**` what you can do now that you could not last week, with the evidence (which check, what happened). If nothing: say so in one sentence.
   - `**What went wrong:**` the checks you skipped or failed, and the one habit behind it.
   - `**What you learned:**` the concrete things, in your words where you said them.
   - `**Learn next:**` the one check waiting for you this week, and what it will prove.
   - `**How you worked with Claude:**` the week's working numbers next to last week's (correction prompts, actions you rejected, interrupts, "don't understand" prompts, prompts with a done-when, agent runs, paid-run guard blocks) read as a story in 2–4 sentences: what got smoother, what still costs you turns, and one thing to try. Noise moves these numbers too, so name a change only when it is large or repeats two weeks; never praise or blame a small wobble. (The user, 2026-10-12: the weekly review is for learning *and* for how they use Claude, what they do better than last time; `/insights` is for longer stretches.)
   - `**Context:**` one line on the workload beside it (prompts, agent runs, paid runs) and anything the machinery did wrong.
   Judge against the loop in `profile.md` ("How learning works here") only; the questions below are what to look at, not extra bullets:
   - Was a concept introduced this week with a source and an "after this you can:" line (loop step 1)? Did reading follow a wrong rating (step 4)?
   - The questions line: asked by kind (code, mechanism, failure, trade-off), answered, with sure/unsure said. Which records were added to `progress.md` this week, and what each says the user can do now. Is a redo of the same kind of check due (~3 and ~10 days after a record)?
   - The terms line: which CS terms the user used in their own prompts this week (count and words, next to last week's), and how many terms Claude set out as a line. A term the user used and defended moves to `progress.md` "Words you used" in step 4; a week with 0 is said plainly under "What went wrong" only if it repeats.
   - Was a prediction written before a paid run this week, and did the run confirm it (the run's own report)?
   - Which concept comes next, from "Now" in `profile.md`.
   - Prompt changes this week: were they shown to the user before the run?
   The "Background only" counts (corrections, done-when, subagents…) feed the "How you worked with Claude" paragraph as a comparison with last week, never as a target to hit.
4. Update `profile.md`, and `progress.md` "Words you used", only from evidence a check produced: a code question rated, a pre-run prediction scored against the run, a monthly test score. Never from keyword counts alone, and never from your own earlier verdicts. Date every change; move a concept between Strong / Developing / Revisit only with that evidence. Keep the user's own words.
5. Do not propose new files, hooks, skills or rules; the user builds those when they ask for them.
6. If the week shows a lesson about working with Claude, add a dated line to `agentic-coding.md` under "Lessons learned".
7. Tell the user in two lines that the weekly review is done and where to read it, then continue with their request.

**Headless run (the Monday task gives you Read, Glob and Grep only, no Edit):** do not try to edit. End your output with the interpretation bullets between a line `<<<INTERPRETATION` and a line `INTERPRETATION>>>`, and the exact profile.md / agentic-coding.md changes you would have made between `<<<PROFILE` and `PROFILE>>>` (file, section, the line to add). `run_weekly.ps1` writes the first block into weekly.md and marks the second as pending; the next interactive session applies it.

Never copy document content or long prompts into these files; counts and short quotes only.
