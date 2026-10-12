#!/bin/sh
# Weekly learning review for cron (macOS / Linux), e.g. Mondays 08:00:
#   0 8 * * 1  sh ~/.claude/learning/run_weekly.sh
# Writes this week's counts, then runs Claude headless with the weekly-review skill to
# interpret them and update profile.md. Claude may only read, and edit files in this
# folder; nothing else. The SessionStart hook is the fallback if a run is missed (laptop
# asleep at 08:00). python3 and claude must be on cron's PATH; set PATH in the crontab if not.

LEARNING="$HOME/.claude/learning"
LOG="$LEARNING/weekly_run.log"
cd "$LEARNING" || exit 1

echo "=== $(date +%Y-%m-%dT%H:%M:%S) start" >> "$LOG"
python3 "$LEARNING/weekly_stats.py" --force >> "$LOG" 2>&1

claude -p "/weekly-review" \
    --permission-mode acceptEdits \
    --allowedTools "Read" "Edit" "Write" "Glob" "Grep" \
    >> "$LOG" 2>&1
echo "=== $(date +%Y-%m-%dT%H:%M:%S) end, exit $?" >> "$LOG"
