# learning-loop

[← all skills](../README.md)

Learning to be a better engineer while AI agents write most of your code.

When an agent writes the code, you skip the part where you would have learned: you never
struggle with a bug, never trace a value, never have to explain your design. You ship faster
and understand less. This folder is a small setup for Claude Code that puts the learning
back, without slowing the project down:

- **Concepts come when the work needs them**, with one example and a source, and you write
  down what you understood from memory.
- **Claude asks you one real question about the code** at the moments that matter, and
  tracks how sure you were against how right you were.
- **Before you hand a "why" question to agents, you guess first**, so you have something to
  compare their answer with.
- **Once a week, a report** tells you what you learned and what is due next, from evidence,
  not from vibes.

It runs on your machine under `~/.claude/learning/`. Nothing is sent anywhere: the weekly
counts are read from Claude Code's local session files, and only counts and your own short
prompts are used, never tool output (which can hold file contents).

## What is in this folder

| File | What it does |
|---|---|
| [`README.md`](README.md) | This page |
| [`weekly_stats.py`](weekly_stats.py) | Counts the last 7 days of your Claude Code sessions and appends them to `weekly.md`. Run as a `SessionStart` hook (`--hook`) or by hand (`--force`) |
| [`guess_first.py`](guess_first.py) | A `UserPromptSubmit` hook: when a prompt asks for agents without a `guess:`, it reminds Claude to ask you for your guess first |
| [`run_weekly.ps1`](run_weekly.ps1) | Windows only, optional: a script for Task Scheduler that writes the counts and runs `/weekly-review` headless once a week |
| [`settings.example.json`](settings.example.json) | The two hooks, ready to merge into `~/.claude/settings.json` |
| [`CLAUDE.snippet.md`](CLAUDE.snippet.md) | Rules to paste into a project's `CLAUDE.md`: when Claude asks you a code question, how, and how it explains |
| [`templates/`](templates/) | Empty starting copies of `profile.md`, `progress.md` and `agentic-coding.md` |

The interpreting half is a skill: [`skills/weekly-review`](../skills/weekly-review/README.md).

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

An example. The agent just committed a change to how a missing value is handled:

```python
def pick_report(cited, found):
    if cited:
        return cited[0]
    if found:
        return found[0]          # fallback
    return None
```

> **Claude:** This hunk decides which test report goes into the record. Input: `cited = []`,
> `found = ["QTR-12"]`. What comes out, and does the record say it was a fallback?
>
> **You:** Unsure. `"QTR-12"`, from the second branch. Nothing marks it as a fallback, so a
> reviewer can't tell it apart from a cited report.
>
> **Claude:** Right on both. Line 5 fills the field silently; the consequence is a value
> that looks cited but isn't. Logged in `progress.md` as *demonstrated, unsure → right*.

You answered by reading four lines, and the next time you see a fallback you will look for
the flag.

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

A made-up entry after the review has run:

```markdown
## Week ending 2026-10-12

Window: 2026-10-05 to 2026-10-12 (all projects).

- Sessions: 31; prompts: 412; median prompt length: 58 chars
- Projects: Repos-myapp 380, Repos-notes 32
- Habits: 'paper:' pages sent: 1; 'guess:' / 'predict:' guesses written: 3

Background only, no targets:
- Prompts with a 'done when': 4
- Correction prompts ('no,', 'wrong', 'I told you'…): 9
- Actions you rejected: 6; interrupts: 5; auto-mode blocks: 0; paid-run guard blocks: 2
- Subagents: 7 (general-purpose 4, Explore 3)
- Skills: grilling 2, whiteboard 1
- Slash commands: clear 6

Interpretation:
- Evals: introduced Monday, `paper:` page sent Wednesday and marked (2 gaps: what the
  unit of scoring is, why an LLM judge was ruled out). First redo due Saturday.
- Code questions: 4 asked; sure and right 2, unsure and right 1, sure and wrong 1 (a
  fallback read as cited). Reading to the last `return` is still the habit to build.
- Next concept from "Now": CI, when the first workflow is added.
```

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

The skill installs with `npx`; the scripts and templates are copied from a clone of this
repo, because they live in your home folder, not in a skill:

```sh
git clone https://github.com/bobocs50/bobo-cooking-stack.git
cd bobo-cooking-stack
```

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

## Requirements

- Claude Code (the hooks and the skill run there).
- Python 3.9 or newer on `PATH` as `python`, standard library only.
- For `run_weekly.ps1`: Windows, and `python` and `claude` on `PATH`. On macOS or Linux, use
  the `SessionStart` hook alone, or a cron line that runs
  `python ~/.claude/learning/weekly_stats.py --force && claude -p "/weekly-review"`.

## FAQ

**Does anything leave my machine?** No. The scripts read local files and write local files.
The review runs in your own Claude Code session like any other prompt.

**What exactly is read from my sessions?** For the last 7 days: your own prompts (to count
them, measure their length, and spot `paper:`, `guess:` and correction words), which tools,
subagents, skills and slash commands were used, and whether a tool call was rejected or
blocked. Tool results are only scanned in their first 400 characters for those markers and
are never written anywhere.

**Will it nag me?** The weekly review asks nothing; it writes and tells you in two lines.
The code question comes at most about once a day, only after risky changes. The guess
reminder fires only when you ask for agents.

**Why are the counts "background only"?** Because they are easy to game and easy to
misread: more corrections can mean you got more precise, not worse. The profile changes only
when a check produced evidence.

**How do I turn it off?** Remove the two hooks from `~/.claude/settings.json` and the
snippet from your `CLAUDE.md`. Your files in `~/.claude/learning/` stay.

**Can I share my profile?** You can, but it describes you and your work. The templates here
are empty on purpose.

## Credits

The teach-first, explain-it-back part is modelled on
[nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise).
