# weekly-review

[← all skills](../../README.md)

Once a week, turns the raw counts in `~/.claude/learning/weekly.md` into 3–5 plain bullets
on how your learning went, and updates your learning profile. Counts alone mislead: "9
correction prompts" could mean you got sloppier or more precise, and a profile that moves on
counts becomes a score you optimise. So the profile changes only when something was checked:
a marked `paper:` page, an answered code question, a test you took.

## How it works

1. Finds the newest `weekly.md` entry still marked `Interpretation: pending` (runs
   `weekly_stats.py --force` if there is none).
2. Reads `profile.md`, `progress.md`, the earlier weeks, and your newest `/insights` report if
   there is one.
3. Writes 3–5 bullets in place of `pending`: the concept checked this week and whether a redo
   is due, the next concept from "Now", and how sure against how right you were on code questions.
4. Updates `profile.md`, dated, only from that evidence. Its own earlier verdicts do not count.
5. Proposes nothing new if your profile declares a freeze.
6. Logs a lesson about working with Claude in `agentic-coding.md`, if the week shows one.
7. Tells you in two lines where to read it. It asks you no questions.

## Example

Claude finds your `paper:` page on evals with two gaps marked and four answered code
questions, and writes:

```markdown
Interpretation:
- Evals: page sent Wednesday, 2 gaps (unit of scoring, why no LLM judge). Redo due Saturday.
- Code questions: 4; sure and right 2, unsure and right 1, sure and wrong 1 (a fallback read
  as cited). Habit to build: read to the last `return` before answering.
- Next from "Now": CI, when the first workflow is added.
```

"Evals" stays under Developing in `profile.md`, because the page had gaps.

## Install

It is installed with the rest of the [learning-by-building setup](../README.md#install),
which also adds the scripts and templates in `~/.claude/learning/` it needs. A scheduled job
runs it weekly; type `/weekly-review` to run it by hand.

Full rules: [`SKILL.md`](SKILL.md).
