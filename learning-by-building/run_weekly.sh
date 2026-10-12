#!/bin/sh
# Weekly learning review for cron (macOS / Linux), e.g. Mondays 08:00:
#   0 8 * * 1  sh ~/.claude/learning/run_weekly.sh
# Writes this week's counts, then runs Claude headless with the weekly-review skill,
# read-only: a non-interactive Claude may not edit files under ~/.claude, so the skill
# prints its judgement between markers and weekly_stats.py --apply writes it into weekly.md.
# Profile changes are noted as pending and applied by the next interactive session
# (SessionStart hook). The hook is also the fallback if a run is missed (laptop asleep at
# 08:00). python3 and claude must be on cron's PATH; set PATH in the crontab if not.

LEARNING="$HOME/.claude/learning"
LOG="$LEARNING/weekly_run.log"
OUT="$LEARNING/weekly_claude.out"
cd "$LEARNING" || exit 1

echo "=== $(date +%Y-%m-%dT%H:%M:%S) start" >> "$LOG"
python3 "$LEARNING/weekly_stats.py" --force >> "$LOG" 2>&1

claude -p "/weekly-review" \
    --allowedTools "Read" "Glob" "Grep" \
    > "$OUT" 2>&1
echo "--- claude exit $?" >> "$LOG"
cat "$OUT" >> "$LOG"

python3 "$LEARNING/weekly_stats.py" --apply "$OUT" >> "$LOG" 2>&1
python3 "$LEARNING/weekly_stats.py" --html >> "$LOG" 2>&1
echo "=== $(date +%Y-%m-%dT%H:%M:%S) end" >> "$LOG"
