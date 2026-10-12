# weekly-review

Once a week, turns the counts in `~/.claude/learning/weekly.md` into 3–5 plain bullets on
how your learning went, and updates your learning profile, but only from evidence a check
produced: a `paper:` page that was marked, a guess scored against real output, an answered
code question. Never from the counts alone.

It is one part of the [learning loop](../../learning-loop/README.md); the counts come from
`learning-loop/weekly_stats.py`.

## Install

```sh
npx skills@latest add bobocs50/bobo-cooking-stack --skill weekly-review
```

Then set up the rest of the loop: the scripts, the hooks and your profile, as in the
[learning loop's install section](../../learning-loop/README.md#install).

## Run

It runs on its own: the `SessionStart` hook tells Claude a review is due, or a scheduled task
runs `claude -p "/weekly-review"`. By hand: `/weekly-review` or "weekly review".

## What it reads and writes

| Reads | Writes |
|---|---|
| `weekly.md` (the newest pending entry), `profile.md`, `progress.md`, your newest `/insights` report if there is one | The interpretation in `weekly.md`; dated changes in `profile.md`; a dated lesson in `agentic-coding.md` if the week shows one |

It asks you nothing, copies no document content and no long prompts, and respects a freeze
declared in `profile.md`.
