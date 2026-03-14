#Requires -RunAsAdministrator
<#
  Fix-CloudflaredAPIRoute.ps1

  PROBLEM: code.stratapp.org/api/* returns 404 because:
    - IIS URL Rewrite rule cannot proxy to http://127.0.0.1:8000 without ARR installed
    - ARR (Application Request Routing) is NOT installed on this machine

  FIX: Use Cloudflare tunnel path-based routing to send /api/* directly to
  the FastAPI backend on port 8000, bypassing IIS entirely.

  Run once in an elevated (Admin) PowerShell.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TunnelID   = "ad9f3beb-b990-4dc6-baec-8b8848f20ab6"
$DestDir    = "C:\ProgramData\cloudflared"
$DestCreds  = "$DestDir\$TunnelID.json"
$ConfigFile = "$DestDir\config-stratapp.yml"

Write-Host "[1] Writing updated Cloudflare tunnel config with path-based API routing..."

$yaml = @"
tunnel: $TunnelID
credentials-file: $DestCreds
# noTLSVerify: cloudflared on Windows cannot load the system root cert pool.
originRequest:
  noTLSVerify: true

ingress:
  - hostname: api.stratapp.org
    service: https://localhost:443
    originRequest:
      noTLSVerify: true

  # Route /api/* directly to FastAPI (port 8001) - no IIS/ARR needed
  - hostname: code.stratapp.org
    path: ^/api
    service: http://127.0.0.1:8001

  # SPA static files served by IIS
  - hostname: code.stratapp.org
    service: https://localhost:443
    originRequest:
      noTLSVerify: true

  - hostname: stratapp.org
    service: http://localhost:80

  - hostname: www.stratapp.org
    service: http://localhost:80

  - service: http_status:404
"@

Set-Content -Path $ConfigFile -Value $yaml -Encoding UTF8
Write-Host "    Config written."

Write-Host "[2] Restarting Cloudflared service..."
Restart-Service -Name "Cloudflared" -Force
Start-Sleep -Seconds 6
$svc = Get-Service -Name "Cloudflared"
Write-Host "    Service status: $($svc.Status)"

if ($svc.Status -ne "Running") {
    Write-Warning "Cloudflared did not start. Check Event Log:"
    Get-EventLog -LogName Application -Source "*cloudflared*" -Newest 5 |
        Select-Object TimeGenerated, Message | Format-List
    exit 1
}

Write-Host "[3] Waiting 10s for tunnel to register routes..."
Start-Sleep -Seconds 10

Write-Host "[4] Smoke-testing FastAPI directly on port 8001..."
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "    FastAPI direct: HTTP $($r.StatusCode) - $($r.Content)"
} catch {
    Write-Warning "    FastAPI direct test failed: $_"
    Write-Host "    Start the backend: cd CodeAnalysis; .venv\Scripts\python.exe -m uvicorn api.server:app --host 0.0.0.0 --port 8001"
}

Write-Host ""
Write-Host "Done. /api/* on code.stratapp.org now routes directly to FastAPI on port 8001."
