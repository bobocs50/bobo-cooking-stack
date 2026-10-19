<div align="center">

# learning-by-building

*Learn to be a better engineer while AI agents write most of your code.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../LICENSE)

[All skills](../README.md)

</div>

When an agent writes the code, you skip the part where you would have learned. This small
Claude Code setup puts the learning back without slowing the project down. Everything stays in
`~/.claude/learning/`; only counts and your own prompts are used, never tool output.

---

## How it works

| Topic | Description |
|---|---|
| Concepts in the work | A concept comes when the work needs it, with an example and a source, and a check waiting |
| One question per risky change | After a commit that decides a value, or before a paid run, Claude shows the changed lines and asks one question, about once a day at most |
| Four kinds | Code (what comes out), mechanism (the textbook term), failure (what reaches the user), trade-off (why this design) |
| Sure or unsure | You say how sure you are first; the gap between sure and right is tracked |
| Terms | Standard CS words from the `## Terms` table in `progress.md`; the weekly count shows which became yours |
| Weekly job | `weekly_stats.py` counts the week, then [weekly-review](weekly-review/README.md) writes the report |
| Fallback | A `SessionStart` hook says the review is due when the weekly job was missed |

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
> **Claude:** Right. Line 5 fills the field silently. Logged as *unsure, right*.

## Files

| Topic | Description |
|---|---|
| [weekly-review/](weekly-review/README.md) | The skill that reads the week and updates your profile |
| [weekly_stats.py](weekly_stats.py) | Counts the last 7 days into `weekly.md`; `--force`, `--hook`, `--apply`, `--html` |
| [weekly_page.py](weekly_page.py) | Renders one offline progress page from the profile, progress and weekly files |
| [run_weekly.sh](run_weekly.sh) / [run_weekly.ps1](run_weekly.ps1) | The weekly job for cron or Windows Task Scheduler |
| [settings.example.json](settings.example.json) | The `SessionStart` fallback hook |
| [CLAUDE.snippet.md](CLAUDE.snippet.md) | The question rules for a project's `CLAUDE.md` |
| [templates/](templates/) | Empty `profile.md`, `progress.md` and `agentic-coding.md` |

---

## Install

```sh
# On Windows: run this in Git Bash and copy run_weekly.ps1 instead of run_weekly.sh
git clone https://github.com/bobocs50/bobo-cooking-stack.git
cd bobo-cooking-stack/learning-by-building
mkdir -p ~/.claude/learning ~/.claude/skills
cp weekly_stats.py weekly_page.py run_weekly.sh ~/.claude/learning/   # Windows: run_weekly.ps1
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

Then merge [settings.example.json](settings.example.json) into `~/.claude/settings.json`, fill in
`~/.claude/learning/profile.md`, and paste [CLAUDE.snippet.md](CLAUDE.snippet.md) into a project's `CLAUDE.md`.

## License

MIT. See [LICENSE](../LICENSE).
