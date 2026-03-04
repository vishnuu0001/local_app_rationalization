#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Recycles the IIS app pools for the backend and frontend sites,
    forces wfastcgi to reload the Flask application, and clears stale
    Python bytecode caches.

.USAGE
    Open PowerShell as Administrator, then run:
        .\Recycle-IIS.ps1

    To target specific pool names:
        .\Recycle-IIS.ps1 -BackendPool "MyBackend" -FrontendPool "MyFrontend"
#>
param(
    [string]$BackendPool  = "",   # leave blank to auto-detect
    [string]$FrontendPool = "",   # leave blank to auto-detect
    [string]$BackendPath  = "E:\techmaapprationalization\local_app_rationalization\backend"
)

$appcmd = "C:\Windows\System32\inetsrv\appcmd.exe"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    WARN: $msg" -ForegroundColor Yellow }

# ── 1. Clear Python __pycache__ so IIS picks up the new .py files ─────────────
Write-Step "Clearing Python bytecode caches under $BackendPath"
Get-ChildItem -Path $BackendPath -Recurse -Filter "__pycache__" -Directory | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    Write-OK "Removed $($_.FullName)"
}

# ── 2. Touch web.config so IIS detects a change and recycles immediately ──────
Write-Step "Touching backend web.config to trigger IIS reload"
$wc = Join-Path $BackendPath "web.config"
if (Test-Path $wc) {
    (Get-Item $wc).LastWriteTime = Get-Date
    Write-OK "Touched $wc"
} else {
    Write-Warn "web.config not found at $wc"
}

# ── 3. Recycle app pools via appcmd ───────────────────────────────────────────
if (Test-Path $appcmd) {

    # Auto-detect pool names if not supplied
    if (-not $BackendPool -or -not $FrontendPool) {
        Write-Step "Auto-detecting app pools..."
        $allPools = & $appcmd list apppool /processModel.userName:* 2>$null |
                    Select-String '"([^"]+)"' | ForEach-Object { $_.Matches[0].Groups[1].Value }
        # fallback: list all pools
        $allPools = (& $appcmd list apppool) -replace '^APPPOOL "([^"]+)".*','$1'
        Write-Host "    Found pools: $($allPools -join ', ')"
    }

    foreach ($pool in @($BackendPool, $FrontendPool) | Where-Object { $_ }) {
        Write-Step "Recycling app pool: $pool"
        $result = & $appcmd recycle apppool /apppool.name:"$pool" 2>&1
        if ($LASTEXITCODE -eq 0) { Write-OK $result }
        else                      { Write-Warn "appcmd returned $LASTEXITCODE`: $result" }
    }

    if (-not $BackendPool -and -not $FrontendPool) {
        Write-Warn "No pool names supplied. Run with -BackendPool and -FrontendPool, or recycle manually:"
        Write-Host "    $appcmd recycle apppool /apppool.name:`"<YourPoolName>`"" -ForegroundColor Gray
    }

} else {
    Write-Warn "appcmd not found. Recycle app pools manually in IIS Manager."
}

# ── 4. Verify health endpoint ─────────────────────────────────────────────────
Write-Step "Checking backend health endpoint..."
Start-Sleep -Seconds 3
try {
    $resp = Invoke-WebRequest -Uri "https://api.stratapp.org/api/health" `
                              -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
    $cors = $resp.Headers["Access-Control-Allow-Origin"]
    Write-OK "HTTP $($resp.StatusCode)"
    if ($cors) { Write-OK "CORS header present: $cors" }
    else        { Write-Warn "CORS header absent on health check (pool may still be warming up)" }
} catch {
    Write-Warn "Health check failed: $_"
    Write-Host "    The pool may still be starting. Wait 10s and retry manually." -ForegroundColor Gray
}

Write-Host "`nDone. If CORS is still missing, run this from a browser console on stratapp.org:" -ForegroundColor Cyan
Write-Host '  fetch("https://api.stratapp.org/api/health",{method:"GET"}).then(r=>console.log([...r.headers]))' -ForegroundColor Gray
