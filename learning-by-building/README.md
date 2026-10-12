# learning-by-building

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
- **Once a week, a scheduled job writes a report** on what you learned and what is due next,
  from evidence, not from vibes.

It runs on your machine under `~/.claude/learning/`. Nothing is sent anywhere: the weekly
counts are read from Claude Code's local session files, and only counts and your own short
prompts are used, never tool output (which can hold file contents).

## What is in this folder

| File | What it does |
|---|---|
| [`README.md`](README.md) | This page |
| [`weekly-review/`](weekly-review/README.md) | The skill that interprets the week: reads the counts and your files, writes the review, updates your profile from evidence |
| [`weekly_stats.py`](weekly_stats.py) | Counts the last 7 days of your Claude Code sessions and appends them to `weekly.md`. `--force` writes an entry now; `--hook` writes one only if 7 days have passed |
| [`run_weekly.sh`](run_weekly.sh) | The weekly job for cron (macOS / Linux): runs `weekly_stats.py --force`, then `claude -p "/weekly-review"` headless |
| [`run_weekly.ps1`](run_weekly.ps1) | The same job for Windows Task Scheduler |
| [`settings.example.json`](settings.example.json) | The `SessionStart` hook, the fallback when the job was missed |
| [`CLAUDE.snippet.md`](CLAUDE.snippet.md) | Rules to paste into a project's `CLAUDE.md`: when Claude asks you a code question, how, and how it explains |
| [`templates/`](templates/) | Empty starting copies of `profile.md`, `progress.md` and `agentic-coding.md` |

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

## The weekly report

A scheduled job runs once a week (for example Mondays 08:00) and does two things:

1. **Count.** `weekly_stats.py --force` reads the last 7 days of your Claude Code sessions,
   across all projects, and appends an entry to `weekly.md` with `Interpretation: pending`:
   - sessions, prompts, median prompt length, projects
   - your habit: `paper:` pages sent
   - background only, never a target: prompts with a "done when", correction prompts,
     actions you rejected, interrupts, subagents and skills used
2. **Interpret.** It runs `claude -p "/weekly-review"` headless. The
   [`weekly-review`](weekly-review/README.md) skill reads the new entry, `profile.md` and
   `progress.md`, writes 3 to 5 plain bullets in place of `Interpretation: pending`, and
   updates your profile, but only from evidence a check produced (a `paper:` page marked, a
   code question answered), never from the counts alone. Claude may only read, and edit
   files in `~/.claude/learning/`.

The job writes its output to `~/.claude/learning/weekly_run.log`.

**The fallback.** If the laptop was off or asleep when the job was due, the `SessionStart`
hook catches it: the first Claude Code session after 7 days writes the counts and tells
Claude to run the review before your first task. While an entry is still pending, every
session start reminds Claude again.

A made-up entry after the review has run:

```markdown
## Week ending 2026-10-12

Window: 2026-10-05 to 2026-10-12 (all projects).

- Sessions: 31; prompts: 412; median prompt length: 58 chars
- Projects: Repos-myapp 380, Repos-notes 32
- Habits: 'paper:' pages sent: 1

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

Everything here is copied from a clone of this repo: the scripts and templates go to
`~/.claude/learning/`, the skill to `~/.claude/skills/weekly-review/`.

```sh
git clone https://github.com/bobocs50/bobo-cooking-stack.git
cd bobo-cooking-stack/learning-by-building
```

**1. Copy the files.**

macOS / Linux:

```sh
mkdir -p ~/.claude/learning ~/.claude/skills
cp weekly_stats.py run_weekly.sh ~/.claude/learning/
cp -n templates/*.md ~/.claude/learning/
cp -r weekly-review ~/.claude/skills/
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\learning", "$HOME\.claude\skills" | Out-Null
Copy-Item weekly_stats.py, run_weekly.ps1 "$HOME\.claude\learning\"
Get-ChildItem templates\*.md | ForEach-Object { $t = "$HOME\.claude\learning\$($_.Name)"; if (-not (Test-Path $t)) { Copy-Item $_.FullName $t } }
Copy-Item -Recurse -Force weekly-review "$HOME\.claude\skills\"
```

Installed as the Claude Code plugin from this repo, the skill comes with it; the files in
step 1 are still needed.

**2. Schedule the weekly job.**

macOS / Linux, with `crontab -e`:

```
0 8 * * 1  sh $HOME/.claude/learning/run_weekly.sh
```

cron runs with a short `PATH`. If `python3` or `claude` is not found (see `weekly_run.log`),
add a `PATH=...` line at the top of the crontab.

Windows PowerShell (runs at the next start if the laptop was off at 08:00):

```powershell
$action   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$HOME\.claude\learning\run_weekly.ps1`""
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 8am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName "Claude weekly learning review" -Action $action -Trigger $trigger -Settings $settings
```

**3. Add the fallback hook.** Merge [`settings.example.json`](settings.example.json) into
`~/.claude/settings.json` (into an existing `"hooks"` block if there is one).

**4. Fill in your profile.** The top of `~/.claude/learning/profile.md`: who you are, what
you want to become, what you already know.

**5. Turn on the code questions** in a project: paste [`CLAUDE.snippet.md`](CLAUDE.snippet.md)
into its `CLAUDE.md`.

**Check it works:** `python ~/.claude/learning/weekly_stats.py --force` writes an entry to
`weekly.md` now, whatever the date. Then `/weekly-review` in Claude Code interprets it.

## Requirements

- Claude Code; the `claude` command on `PATH` for the scheduled job.
- Python 3.9 or newer, standard library only (`python3` for cron, `python` for the hook and
  on Windows).
- A scheduler: cron on macOS / Linux, Task Scheduler on Windows. Without one, the hook alone
  still runs the review in the first session of each new week.

## FAQ

**Does anything leave my machine?** No. The scripts read local files and write local files.
The review runs in your own Claude Code, like any other prompt.

**What exactly is read from my sessions?** For the last 7 days: your own prompts (to count
them, measure their length, and spot `paper:` and correction words), which tools, subagents,
skills and slash commands were used, and whether a tool call was rejected or blocked. Tool
results are only scanned in their first 400 characters for those markers and are never
written anywhere.

**Why a scheduled job and a hook?** The job runs the review even when you do not open
Claude Code that day. The hook catches the weeks the job missed, because the laptop was off.
The hook only writes when 7 days have passed since the last entry, so in a normal week it
stays quiet. One rare double: a session opened on the job's day before the job runs; delete
the extra entry in `weekly.md` if it bothers you.

**Will it nag me?** The weekly review asks nothing; it writes and tells you in two lines.
The code question comes at most about once a day, only after risky changes.

**Why are the counts "background only"?** Because they are easy to game and easy to
misread: more corrections can mean you got more precise, not worse. The profile changes only
when a check produced evidence.

**How do I turn it off?** Delete the cron line or the scheduled task, remove the hook from
`~/.claude/settings.json` and the snippet from your `CLAUDE.md`. Your files in
`~/.claude/learning/` stay.

**Can I share my profile?** You can, but it describes you and your work. The templates here
are empty on purpose.

## Credits

The teach-first, explain-it-back part is modelled on
[nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise).
