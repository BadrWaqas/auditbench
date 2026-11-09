$ErrorActionPreference = "Stop"
$base = "C:\Users\Badrw\Projects\auditbench\manual"
$out = Join-Path $base "claude-opus-5.5_chat"
$prompts = Get-ChildItem (Join-Path $base "prompts") -Filter "*_hard_*.txt" | Sort-Object Name
Write-Host "AuditBench - Opus 5.5 manual run (hard tier)" -ForegroundColor Green
Write-Host "In claude.ai: pick Opus 5.5. For EACH prompt use a NEW chat (and no extra instructions)." -ForegroundColor Yellow
foreach ($p in $prompts) {
    $task = $p.BaseName -replace '^\d+_', ''
    $dest = Join-Path $out ("{0}__1.txt" -f $task)
    if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 20)) { Write-Host "skip $task (already saved)"; continue }
    Set-Clipboard -Value (Get-Content $p.FullName -Raw)
    Write-Host ""
    Write-Host ("[{0}] Prompt COPIED. Open a NEW Claude chat, press Ctrl+V, send." -f $p.BaseName) -ForegroundColor Cyan
    Read-Host  "When Claude has finished, click Claude's COPY button under its reply, then press Enter here"
    $reply = Get-Clipboard -Raw
    while (-not $reply -or $reply.TrimStart().StartsWith("You are a senior data scientist") -or $reply -notmatch '"flaw"') {
        Write-Host "That is not Claude's answer (it is the question, or has no JSON line at the end)." -ForegroundColor Red
        Write-Host "If you have NOT sent it yet: press Ctrl+V in a NEW Claude chat now (the question is on your clipboard again)." -ForegroundColor Red
        Set-Clipboard -Value (Get-Content $p.FullName -Raw)
        Read-Host "When Claude has answered, click the COPY icon under ITS reply, then press Enter here"
        $reply = Get-Clipboard -Raw
    }
    [IO.File]::WriteAllText($dest, $reply, (New-Object System.Text.UTF8Encoding $false))
    Write-Host ("saved {0} ({1} characters)" -f $task, $reply.Length) -ForegroundColor Green
}
Write-Host ""
Write-Host "ALL DONE. Tell Claude 'opus done'. You can close this window." -ForegroundColor Green
