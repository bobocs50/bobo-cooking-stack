# learning-by-building

[← all skills](../README.md)

Learning to be a better engineer while AI agents write most of your code. When an agent
writes the code, you skip the part where you would have learned. This small setup for
Claude Code puts the learning back without slowing the project down.

## How it works

1. **Concepts come when the work needs them**, with an example and a source. You write what
   you know from memory and send it as `paper: ...`; Claude marks only what is wrong.
2. **One code question at risky commits.** After a commit that decides a value (null
   handling, fallbacks, swallowed errors, a weakened test), or before a paid run, Claude
   shows the hunk and asks one question, about once a day at most. You say sure or unsure
   first; the gap between how sure and how right you were is tracked.
3. **A weekly job writes a report.** `weekly_stats.py` counts your last 7 days, then
   `claude -p "/weekly-review"` updates your profile, only from evidence a check produced.
4. **The `SessionStart` hook is the fallback** when the job was missed (laptop off).
5. Nothing leaves your machine: everything lives in `~/.claude/learning/`, and only counts
   and your own prompts are used, never tool output.

## Example

```python
def pick_report(cited, found):
    if cited:
        return cited[0]
    if found:
        return found[0]          # fallback
    return None
```

> **Claude:** Input: `cited = []`, `found = ["QTR-12"]`. What comes out, and does the record say it was a fallback?
>
> **You:** Unsure. `"QTR-12"`, and nothing marks it as a fallback.
>
> **Claude:** Right. Line 5 fills the field silently. Logged as *unsure → right*.

## Install

On Windows, run the copy step in Git Bash and copy `run_weekly.ps1` instead of `run_weekly.sh`.

```sh
git clone https://github.com/bobocs50/bobo-cooking-stack.git
cd bobo-cooking-stack/learning-by-building
mkdir -p ~/.claude/learning ~/.claude/skills
cp weekly_stats.py run_weekly.sh ~/.claude/learning/   # Windows: run_weekly.ps1
cp -n templates/*.md ~/.claude/learning/
cp -r weekly-review ~/.claude/skills/
```

Schedule the weekly job. macOS / Linux, with `crontab -e`:

```
0 8 * * 1  sh $HOME/.claude/learning/run_weekly.sh
```

Windows PowerShell:

```powershell
$action   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$HOME\.claude\learning\run_weekly.ps1`""
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 8am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName "Claude weekly learning review" -Action $action -Trigger $trigger -Settings $settings
```

Then merge [`settings.example.json`](settings.example.json) into `~/.claude/settings.json`, fill in
`~/.claude/learning/profile.md`, and paste [`CLAUDE.snippet.md`](CLAUDE.snippet.md) into a project's `CLAUDE.md`.

## Files

| File | What it does |
|---|---|
| [`weekly-review/`](weekly-review/README.md) | The skill that interprets the week and updates your profile |
| [`weekly_stats.py`](weekly_stats.py) | Counts the last 7 days of sessions into `weekly.md` (`--force` now, `--hook` only after 7 days) |
| [`run_weekly.sh`](run_weekly.sh) / [`run_weekly.ps1`](run_weekly.ps1) | The weekly job for cron / Windows Task Scheduler |
| [`settings.example.json`](settings.example.json) | The `SessionStart` fallback hook |
| [`CLAUDE.snippet.md`](CLAUDE.snippet.md) | The code-question rules for a project's `CLAUDE.md` |
| [`templates/`](templates/) | Empty `profile.md`, `progress.md` and `agentic-coding.md` |

Full rules for the review: [`weekly-review/SKILL.md`](weekly-review/SKILL.md).
