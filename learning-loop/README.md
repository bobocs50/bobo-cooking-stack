# learning-loop

Learning to be a better engineer while AI agents write most of the code. Most of the code
gets written for you, and you can still learn by reading, predicting and explaining it.
This folder is the setup that makes that happen inside Claude Code: what Claude does, when
it asks you something, and a weekly report on how you are doing.

It runs on your machine under `~/.claude/learning/`. Nothing is sent anywhere; the weekly
report reads only counts and your own short prompts from Claude Code's local session files,
never tool output.

## The loop, per concept

A concept is a topic area (evals, CI/CD, system design, fine-tuning), not a vocabulary
word. It is introduced when the work needs it, not on a schedule.

1. **Claude introduces it** with one concrete example (from your project or made up) and
   one or two sources.
2. **You study it**, about 30 minutes, from the sources.
3. **You write down what you know**, from memory, on paper, and send it as `paper: ...`.
   Claude marks only what is wrong or missing.
4. **You explain it** to people (a team meeting, a study group).

Redo step 3 after about 3 and about 10 days when the concept matters; once is not enough.

## Questions while you build

The most useful learning moment is the code you are about to trust. Claude asks you **one
question about one hunk**, about once a day at most, at two moments:

1. **Right after a risky commit**: one that decides a value (null handling, fallbacks,
   merge rules, error paths that swallow a failure, cache keys, a deleted or weakened
   test). A reviewer subagent that sees only the diff runs first; then Claude shows you
   the hunk (about 40 lines at most, with one sentence on what it decides) and asks.
2. **Before a paid or long run**: the hunk that run will test. Your answer is the
   prediction the run's numbers then check.

The question rotates between kinds, so it cannot be answered from the commit message:
what comes out for this input; find the defect or say none; which caller still assumes
the old shape; why this and not null; which test line would still pass if the fix were
wrong. Never yes/no, never style. You say **sure** or **unsure** first, answer in two or
three sentences, and Claude corrects in one line naming the line and the consequence. The
gap between how sure you were and how right you were is what you track.

Paste [`CLAUDE.snippet.md`](CLAUDE.snippet.md) into a project's `CLAUDE.md` to switch
this on there.

## Struggle first

Before you hand a *why* question to agents ("why does this value miss", "why did the run
get worse"), spend 15 minutes on it yourself: look at the data, write your guess as
`guess: I think X because Y`. Then the agents check it, and when their findings come back
you say which hold before Claude gives its verdict.

`guess_first.py` is a `UserPromptSubmit` hook that reminds Claude of this whenever a
prompt asks for a swarm or agents without a `guess:` or `skip`. It never blocks a prompt.

## The weekly report

Once a week `weekly_stats.py` counts how you worked with Claude Code over the last 7 days,
across all projects, and appends the counts to `weekly.md` with `Interpretation: pending`:

- sessions, prompts, median prompt length, projects
- your habits: `paper:` pages sent, `guess:` guesses written
- background only, never a target: prompts with a "done when", correction prompts,
  actions you rejected, interrupts, subagents and skills used

Then the [`weekly-review`](../skills/weekly-review/README.md) skill reads the counts,
`profile.md` and `progress.md`, writes 3 to 5 plain bullets in place of
`Interpretation: pending`, and updates your profile, but only from evidence a check
produced (a `paper:` page marked, a guess scored against real output), never from the
counts alone.

Two ways it runs, use either or both:

- **A `SessionStart` hook**: the first session of a new week writes the counts and tells
  Claude to run the review before your first task.
- **A scheduled task** (Windows: `run_weekly.ps1` from Task Scheduler, e.g. Mondays 08:00):
  writes the counts and runs Claude headless with `/weekly-review`, allowed only to read
  and to edit files in this folder.

## Your files

| File | What it holds | Who writes it |
|---|---|---|
| `profile.md` | Background, goal, how your loop works, the concepts, how you read code, Strong / Developing / Revisit | You set it up; the weekly review updates it, dated, only from evidence |
| `progress.md` | Per concept: when it was introduced, what you demonstrated, what needs reinforcement, sources | Claude, after each concept step and each answered question |
| `agentic-coding.md` | How you work with agents now, lessons learned, setup changes, what to try next | You and Claude, dated lines |
| `weekly.md` | One entry per week: the counts and the interpretation | `weekly_stats.py`, then the review |

Starting copies are in [`templates/`](templates/). They stay on your machine; do not commit
your filled-in versions anywhere public, they describe you and your work.

## Install

macOS / Linux:

```sh
mkdir -p ~/.claude/learning
cp learning-loop/weekly_stats.py learning-loop/guess_first.py ~/.claude/learning/
cp -n learning-loop/templates/*.md ~/.claude/learning/
npx skills@latest add bobocs50/bobo-cooking-stack --skill weekly-review
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\learning" | Out-Null
Copy-Item learning-loop\weekly_stats.py, learning-loop\guess_first.py, learning-loop\run_weekly.ps1 "$HOME\.claude\learning\"
Get-ChildItem learning-loop\templates\*.md | ForEach-Object { $t = "$HOME\.claude\learning\$($_.Name)"; if (-not (Test-Path $t)) { Copy-Item $_.FullName $t } }
npx skills@latest add bobocs50/bobo-cooking-stack --skill weekly-review
```

Then add the hooks from [`settings.example.json`](settings.example.json) to
`~/.claude/settings.json` (merge them into an existing `"hooks"` block), and fill in the
top of `profile.md`: who you are, what you want to become, what you already know.

Check it works: `python ~/.claude/learning/weekly_stats.py --force` writes an entry to
`weekly.md` now, whatever the date.

## Credits

The teach-first, explain-it-back part is modelled on
[nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise).
