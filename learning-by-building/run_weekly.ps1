# Weekly learning review, started by a Windows scheduled task (e.g. Mondays 08:00, or at the
# next start if the laptop was off). Writes this week's counts, then runs Claude headless with
# the weekly-review skill, read-only: a non-interactive Claude may not edit files under
# ~/.claude, so the skill prints its judgement between markers and weekly_stats.py --apply
# writes it into weekly.md. Profile changes are noted as pending and applied by the next
# interactive session (SessionStart hook). The hook is also the fallback if this task is
# missed. python and claude must be on PATH.

$ErrorActionPreference = "Continue"
$learning = Join-Path $env:USERPROFILE ".claude\learning"
$log = Join-Path $learning "weekly_run.log"
$out = Join-Path $learning "weekly_claude.out"
Set-Location $learning

# Out-File -Encoding utf8, not *>>: redirection writes UTF-16 on Windows PowerShell 5.1.
"=== $(Get-Date -Format s) start" | Out-File -FilePath $log -Append -Encoding utf8
& python (Join-Path $learning "weekly_stats.py") --force 2>&1 | Out-File -FilePath $log -Append -Encoding utf8

& claude -p "/weekly-review" `
    --allowedTools "Read" "Glob" "Grep" `
    2>&1 | Out-File -FilePath $out -Encoding utf8
"--- claude exit $LASTEXITCODE" | Out-File -FilePath $log -Append -Encoding utf8
Get-Content $out | Out-File -FilePath $log -Append -Encoding utf8

& python (Join-Path $learning "weekly_stats.py") --apply $out 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
"=== $(Get-Date -Format s) end" | Out-File -FilePath $log -Append -Encoding utf8
