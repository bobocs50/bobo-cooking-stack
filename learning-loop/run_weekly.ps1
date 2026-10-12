# Weekly learning review, started by a Windows scheduled task (e.g. Mondays 08:00, or at the
# next start if the laptop was off). Writes this week's counts, then runs Claude headless with
# the weekly-review skill to interpret them and update profile.md. Claude may only read, and
# edit files in this folder; nothing else. The SessionStart hook in ~/.claude/settings.json is
# the fallback if this task is missed. python and claude must be on PATH.

$ErrorActionPreference = "Continue"
$learning = Join-Path $env:USERPROFILE ".claude\learning"
$log = Join-Path $learning "weekly_run.log"
Set-Location $learning

"=== $(Get-Date -Format s) start" | Out-File -FilePath $log -Append -Encoding utf8
& python (Join-Path $learning "weekly_stats.py") --force *>> $log

& claude -p "/weekly-review" `
    --permission-mode acceptEdits `
    --allowedTools "Read" "Edit" "Write" "Glob" "Grep" `
    *>> $log
"=== $(Get-Date -Format s) end, exit $LASTEXITCODE" | Out-File -FilePath $log -Append -Encoding utf8
