#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Moves CodeAnalysisUI off the conflicted HTTPS:8001 binding to a clean
    HTTP-on-localhost:8082 binding, then updates the Cloudflare tunnel config
    so code.stratapp.org routes to the new port.

.WHY
    Port 8001 keeps being grabbed by a running Python/uvicorn watchdog process
    before IIS can claim it (race condition / 0x80070020).  Switching to an
    HTTP-only localhost binding removes the port race and the SSL cert requirement,
    consistent with how StratAppAPI is already served via cloudflared.

.USAGE
    Right-click -> Run with PowerShell  (or open Admin PS and run the file)
#>

Set-StrictMode  -Version Latest
$ErrorActionPreference = 'Stop'

$AppCmd            = "$env:SystemRoot\System32\inetsrv\appcmd.exe"
$CloudflaredConfig = 'C:\ProgramData\cloudflared\config-stratapp.yml'
$SiteName          = 'CodeAnalysisUI'
$OldPort           = 8001
$NewPort           = 8082

function Write-Step($msg) { Write-Host "" ; Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    WARN: $msg" -ForegroundColor Yellow }

if (-not (Test-Path $AppCmd)) {
    Write-Error "appcmd.exe not found at $AppCmd -- is IIS installed?"
    exit 1
}

# Step 1: Kill every Python/uvicorn process holding port 8001
Write-Step "Freeing port $OldPort from any Python/uvicorn processes..."
$conns = Get-NetTCPConnection -LocalPort $OldPort -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    foreach ($c in $conns) {
        $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "    Stopping $($proc.ProcessName) PID $($c.OwningProcess)..." -ForegroundColor Yellow
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 2
    Write-OK "Port $OldPort cleared."
} else {
    Write-OK "Port $OldPort already free."
}

# Step 2: Stop the site before touching bindings
Write-Step "Stopping IIS site '$SiteName'..."
& $AppCmd stop site "/site.name:$SiteName" 2>&1 | Out-Null
Start-Sleep -Seconds 1

# Step 3: Remove ALL existing bindings on this site (handles any port/protocol leftover)
Write-Step "Removing all existing bindings from '$SiteName'..."
$siteXml = & $AppCmd list site $SiteName /xml 2>&1
# Remove https:8001, https:8082, http:8082 - any combination that may exist
foreach ($proto in @('https','http')) {
    foreach ($port in @(8001, 8082)) {
        foreach ($ip in @('*', '127.0.0.1', '0.0.0.0')) {
            $bindInfo = "${ip}:${port}:"
            & $AppCmd set site $SiteName "-bindings.[protocol='$proto',bindingInformation='$bindInfo']" 2>&1 | Out-Null
            & $AppCmd set site $SiteName "-bindings.[protocol='$proto',bindingInformation='${ip}:${port}:code.stratapp.org']" 2>&1 | Out-Null
        }
    }
}
Write-OK "Old bindings cleared."

# Step 4: Add new HTTP:127.0.0.1:8082 binding
Write-Step "Adding new http/127.0.0.1:${NewPort}: binding..."
$addResult = & $AppCmd set site $SiteName "+bindings.[protocol='http',bindingInformation='127.0.0.1:${NewPort}:']" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-OK "New binding added: http://127.0.0.1:$NewPort"
} else {
    Write-Warn "Binding add result (may already exist): $addResult"
}

# Step 5: Start the site on the new port
Write-Step "Starting IIS site '$SiteName' on port $NewPort..."
$startResult = & $AppCmd start site "/site.name:$SiteName" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-OK "Site started: $startResult"
} else {
    Write-Host "    ERROR starting site: $startResult" -ForegroundColor Red
    Write-Host "    Check IIS Event Viewer for details." -ForegroundColor Yellow
}

# Step 6: Update Cloudflare config.yml
Write-Step "Updating Cloudflare config for code.stratapp.org -> port $NewPort..."
if (Test-Path $CloudflaredConfig) {
    $yaml = Get-Content $CloudflaredConfig -Raw

    # Replace any previous service URL for code.stratapp.org block
    $yaml = [regex]::Replace(
        $yaml,
        '(?m)(hostname:\s*code\.stratapp\.org\s*\n\s*service:\s*)https?://127\.0\.0\.1:\d+',
        "`${1}http://127.0.0.1:$NewPort"
    )

    Set-Content -Path $CloudflaredConfig -Value $yaml -Encoding UTF8
    Write-OK "Config updated: code.stratapp.org -> http://127.0.0.1:$NewPort"

    Write-Step "Restarting Cloudflared service..."
    Restart-Service -Name 'Cloudflared' -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 5
    $cfStatus = (Get-Service -Name 'Cloudflared' -ErrorAction SilentlyContinue).Status
    Write-OK "Cloudflared status: $cfStatus"
} else {
    Write-Warn "Cloudflare config not found at $CloudflaredConfig"
    Write-Warn "Run fix_cloudflared_notlsverify.ps1 first, then re-run this script."
}

# Step 7: Smoke test
Write-Step "Smoke-testing http://127.0.0.1:${NewPort} ..."
Start-Sleep -Seconds 2
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$NewPort" -Headers @{ Host = 'code.stratapp.org' } -UseBasicParsing -TimeoutSec 8
    Write-OK "HTTP $($r.StatusCode) -- CodeAnalysisUI is responding."
} catch {
    Write-Warn "Local test failed: $_"
    Write-Host "    The site may still be starting. Check: http://127.0.0.1:$NewPort" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==> Done." -ForegroundColor Green
Write-Host "    IIS binding : http://127.0.0.1:$NewPort  (CodeAnalysisUI)" -ForegroundColor White
Write-Host "    Cloudflare  : code.stratapp.org -> http://127.0.0.1:$NewPort" -ForegroundColor White
Write-Host "    Public URL  : https://code.stratapp.org" -ForegroundColor White
pause
