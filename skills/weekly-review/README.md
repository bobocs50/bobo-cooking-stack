# weekly-review

[← all skills](../../README.md)

Once a week, turns the raw counts in `~/.claude/learning/weekly.md` into 3–5 plain bullets
on how your learning went, and updates your learning profile, but only from evidence a check
produced. It is the interpreting half of the [learning loop](../../learning-loop/README.md);
the counting half is `learning-loop/weekly_stats.py`.

## Why it exists

Counts alone mislead. "9 correction prompts this week" could mean you got sloppier or that
you got more precise about what you want. A profile that moves on counts turns into a score
you start optimising. So this skill reads the counts as background and changes your profile
only when something was actually checked: a `paper:` page that was marked, a guess compared
with what the agents found, a code question you answered, a test you took.

## How it works, step by step

1. **Find the pending week.** It reads the newest entry in `weekly.md` that still says
   `Interpretation: pending`. If there is none, it runs
   `python ~/.claude/learning/weekly_stats.py --force` to write one.
2. **Read your record.** `profile.md` (your loop, your concepts, how you read code, "Now"),
   `progress.md`, and the earlier weeks. If you ran Claude Code's `/insights` since the last
   entry, it also reads the newest report and names its date. It never runs `/insights`
   itself.
3. **Write the interpretation**, 3–5 bullets, in place of `Interpretation: pending`, judged
   only against the loop in your profile:
   - which concept was introduced, studied, written as a `paper:` page and checked this
     week, and whether a redo is due (about 3 and 10 days after a page);
   - which concept comes next, from "Now";
   - the code questions: how many were asked, how sure you were against how right, and
     whether a risky change went by without one.
4. **Update `profile.md`**, dated, only from that evidence. A concept moves between Strong,
   Developing and Revisit only with it. Your own words are kept. Its own earlier verdicts do
   not count as evidence.
5. **Respect a freeze.** If your profile declares one ("no new files, hooks, skills or
   rules until <date>"), it proposes nothing new.
6. **Log a lesson** about working with Claude, if the week shows one, as a dated line in
   `agentic-coding.md`.
7. **Tell you in two lines** that the review is done and where to read it, then carry on with
   whatever you asked.

It asks you no questions, and it never copies file contents or long prompts into these
files, only counts and short quotes.

## Example

Monday morning you open Claude Code. The `SessionStart` hook sees that 7 days have passed,
writes this week's counts to `weekly.md`, and tells Claude a review is due. Before your first
task Claude reads the week, finds your `paper:` page on evals from Wednesday with two gaps
marked, and four answered code questions, and writes:

```markdown
Interpretation:
- Evals: page sent Wednesday, 2 gaps (unit of scoring, why no LLM judge). Redo due Saturday.
- Code questions: 4; sure and right 2, unsure and right 1, sure and wrong 1 (a fallback read
  as cited). Habit to build: read to the last `return` before answering.
- Next from "Now": CI, when the first workflow is added.
```

In `profile.md`, "Evals" stays under Developing with a dated note, because the page had gaps.
Then: "Weekly review done, see `~/.claude/learning/weekly.md`." and your task.

## What it reads and writes

| Reads | Writes |
|---|---|
| `weekly.md` (the newest pending entry and the earlier weeks), `profile.md`, `progress.md`, your newest `/insights` report if there is one | The interpretation in `weekly.md`; dated changes in `profile.md`; a dated lesson in `agentic-coding.md` if the week shows one |

## Files

| File | What it is |
|---|---|
| [`SKILL.md`](SKILL.md) | The instructions Claude follows |
| [`README.md`](README.md) | This page |

## Install

```sh
npx skills@latest add bobocs50/bobo-cooking-stack --skill weekly-review
```

The skill alone has nothing to read. Set up the rest of the loop too: the two scripts, the
hooks and your profile, as in the [learning loop's install section](../../learning-loop/README.md#install).

## Run

- **Automatically:** the `SessionStart` hook from `learning-loop/settings.example.json`
  starts it in the first session of a new week; on Windows, `learning-loop/run_weekly.ps1`
  from Task Scheduler runs it headless.
- **By hand:** type `/weekly-review` or "weekly review".

## Limits

- It interprets what the counts and your files show; a week with no `paper:` page, no guess
  and no code question gives a short review that says so.
- It needs `profile.md` filled in. With the empty template it can only report counts.
- It finds `paper:` pages and code questions in your session transcripts, so they must have
  happened in Claude Code.
