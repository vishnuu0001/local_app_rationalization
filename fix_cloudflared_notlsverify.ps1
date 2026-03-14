#Requires -RunAsAdministrator
<#
  fix_cloudflared_notlsverify.ps1

  ROOT CAUSE: cloudflared connects to https://localhost:443 using "localhost"
  as the TLS SNI hostname. The Cloudflare Origin Cert has SANs for *.stratapp.org,
  not "localhost" => TLS hostname mismatch => 502.
  noTLSVerify in a config file is overridden by Cloudflare's remote config push
  when the token is present.

  FIX:
  1. Add a plain HTTP binding on 127.0.0.1:8080 to IIS StratAppAPI (localhost only,
     no TLS at all between cloudflared and IIS).
  2. Write a local config.yml in C:\ProgramData\cloudflared\ (accessible to
     LOCAL SYSTEM) pointing to http://localhost:8080.
  3. Switch the cloudflared service to use that config file instead of --token.

  Run once in an elevated (Admin) PowerShell.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TunnelID       = "ad9f3beb-b990-4dc6-baec-8b8848f20ab6"
$SrcCreds       = "C:\Users\vishn\.cloudflared\$TunnelID.json"
$DestDir        = "C:\ProgramData\cloudflared"
$DestCreds      = "$DestDir\$TunnelID.json"
$ConfigFile     = "$DestDir\config-stratapp.yml"
$CloudflaredExe = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$AppCmd         = "$env:SystemRoot\System32\inetsrv\appcmd.exe"

# ---------- 1. Add HTTP binding 127.0.0.1:8080 to StratAppAPI in IIS -------
Write-Host "[1] Adding HTTP binding on 127.0.0.1:8080 to StratAppAPI ..."

# Check if binding already exists
$existing = & $AppCmd list site "StratAppAPI" 2>&1
if ($existing -match "8080") {
    Write-Host "    Binding already exists, skipping."
} else {
    $result = & $AppCmd set site "StratAppAPI" /+"bindings.[protocol='http',bindingInformation='127.0.0.1:8080:']" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "appcmd failed: $result"
        exit 1
    }
    Write-Host "    Binding added."
}

# Restart IIS to pick up the new binding
Write-Host "    Restarting IIS site ..."
& $AppCmd stop site "StratAppAPI" | Out-Null
Start-Sleep -Seconds 1
& $AppCmd start site "StratAppAPI" | Out-Null
Write-Host "    Site restarted."

# Verify the binding works locally
Start-Sleep -Seconds 2
$test = try { (Invoke-WebRequest -Uri "http://127.0.0.1:8080/api/health" -Headers @{Host="api.stratapp.org"} -UseBasicParsing -TimeoutSec 5).StatusCode } catch { "FAIL: $_" }
Write-Host "    Local HTTP test: $test"

# ---------- 2. Create ProgramData dir and copy credentials -----------------
Write-Host "[2] Setting up C:\ProgramData\cloudflared ..."
if (-not (Test-Path $DestDir)) { New-Item -ItemType Directory -Path $DestDir | Out-Null }
Copy-Item -Path $SrcCreds -Destination $DestCreds -Force
icacls $DestDir /grant "NT AUTHORITY\SYSTEM:(OI)(CI)R" /T | Out-Null
Write-Host "    Credentials copied and SYSTEM access granted."

# ---------- 3. Write config.yml using HTTP (no TLS) to IIS -----------------
Write-Host "[3] Writing $ConfigFile ..."
$yaml = @"
tunnel: $TunnelID
credentials-file: $DestCreds

ingress:
  - hostname: api.stratapp.org
    service: http://127.0.0.1:8080

  # Route /api/* directly to FastAPI (port 8000) - bypasses IIS, no ARR needed
  - hostname: code.stratapp.org
    path: ^/api
    service: http://127.0.0.1:8000

  # SPA static files served by IIS on port 8082
  - hostname: code.stratapp.org
    service: http://127.0.0.1:8082

  - hostname: stratapp.org
    service: http://localhost:80

  - hostname: www.stratapp.org
    service: http://localhost:80

  - service: http_status:404
"@
Set-Content -Path $ConfigFile -Value $yaml -Encoding UTF8
Write-Host "    Written OK."

# ---------- 4. Switch service to config-file mode --------------------------
Write-Host "[4] Updating Cloudflared service to use config file ..."
$newPath = "`"$CloudflaredExe`" --config `"$ConfigFile`" tunnel run"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Cloudflared" -Name "ImagePath" -Value $newPath
Write-Host "    ImagePath: $newPath"

# ---------- 5. Restart cloudflared service ---------------------------------
Write-Host "[5] Restarting Cloudflared service ..."
Restart-Service -Name "Cloudflared" -Force
Start-Sleep -Seconds 8
$svc = Get-Service -Name "Cloudflared"
Write-Host "    Service status: $($svc.Status)"

if ($svc.Status -ne "Running") {
    Write-Warning "Service did not start."
    Get-EventLog -LogName Application -Source "*cloudflared*" -Newest 5 | Select-Object TimeGenerated, Message | Format-List
    exit 1
}

# ---------- 6. Smoke test --------------------------------------------------
Write-Host "[6] Waiting 10 s for tunnel to register ..."
Start-Sleep -Seconds 10
try {
    $r = Invoke-WebRequest -Uri "https://api.stratapp.org/api/health" -UseBasicParsing -TimeoutSec 20
    Write-Host "    SUCCESS - HTTP $($r.StatusCode): $($r.Content)"
} catch {
    Write-Warning "    Smoke test failed: $_"
    Write-Host "    Run: Get-EventLog -LogName Application -Source cloudflared -Newest 10"
}

Write-Host ""
Write-Host "Done."

