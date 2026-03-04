#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Configures IIS sites for the App Rationalization Platform.
    - stratapp.org    → frontend build (static React SPA)
    - api.stratapp.org → backend (Flask via wfastcgi)

.USAGE
    Open PowerShell as Administrator, then run:
        .\Setup-IISSites.ps1

    Optional overrides:
        .\Setup-IISSites.ps1 -BackendPool "AppRat_Backend" -FrontendPool "AppRat_Frontend"
#>
param(
    [string]$BackendPath   = "E:\techmaapprationalization\local_app_rationalization\backend",
    [string]$FrontendPath  = "E:\techmaapprationalization\local_app_rationalization\frontend\build",
    [string]$BackendPool   = "AppRat_Backend",
    [string]$FrontendPool  = "AppRat_Frontend",
    [string]$BackendSite   = "AppRat_API",
    [string]$FrontendSite  = "AppRat_Frontend",
    [string]$PythonExe     = "E:\techmaapprationalization\local_app_rationalization\backend\.venv\Scripts\python.exe",
    [string]$WfastcgiRunner = "E:\techmaapprationalization\local_app_rationalization\backend\wfastcgi_runner.py"
)

Import-Module WebAdministration -ErrorAction Stop

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    WARN: $msg" -ForegroundColor Yellow }

# ── 1. App Pools ──────────────────────────────────────────────────────────────
Write-Step "Configuring App Pools"

foreach ($pool in @($BackendPool, $FrontendPool)) {
    if (-not (Test-Path "IIS:\AppPools\$pool")) {
        New-WebAppPool -Name $pool | Out-Null
        Write-OK "Created pool: $pool"
    } else {
        Write-OK "Pool exists: $pool"
    }
    # No managed code — both pools serve non-.NET apps
    Set-ItemProperty "IIS:\AppPools\$pool" managedRuntimeVersion ""
    Set-ItemProperty "IIS:\AppPools\$pool" processModel.idleTimeout "00:00:00"
    Set-ItemProperty "IIS:\AppPools\$pool" recycling.periodicRestart.time "00:00:00"
}

# ── 2. Frontend site (stratapp.org) ───────────────────────────────────────────
Write-Step "Configuring frontend site: $FrontendSite → $FrontendPath"

if (-not (Test-Path "IIS:\Sites\$FrontendSite")) {
    New-Website -Name $FrontendSite `
                -PhysicalPath $FrontendPath `
                -ApplicationPool $FrontendPool `
                -Port 80 | Out-Null
    Write-OK "Created site: $FrontendSite"
} else {
    Set-ItemProperty "IIS:\Sites\$FrontendSite" physicalPath $FrontendPath
    Write-OK "Updated physical path for: $FrontendSite"
}

# Set hostname bindings for frontend (HTTP + HTTPS)
$existingBindings = Get-WebBinding -Name $FrontendSite
foreach ($fqdn in @("stratapp.org", "www.stratapp.org")) {
    foreach ($proto in @("http", "https")) {
        $port = if ($proto -eq "https") { 443 } else { 80 }
        $info = "*:${port}:${fqdn}"
        if (-not ($existingBindings | Where-Object { $_.bindingInformation -eq $info })) {
            New-WebBinding -Name $FrontendSite -Protocol $proto -Port $port -HostHeader $fqdn
            Write-OK "Added binding: $proto $info"
        } else {
            Write-OK "Binding exists: $proto $info"
        }
    }
}

# ── 3. Backend site (api.stratapp.org) ────────────────────────────────────────
Write-Step "Configuring backend site: $BackendSite → $BackendPath"

if (-not (Test-Path "IIS:\Sites\$BackendSite")) {
    New-Website -Name $BackendSite `
                -PhysicalPath $BackendPath `
                -ApplicationPool $BackendPool `
                -Port 8080 | Out-Null    # temp port; real bindings set below
    Write-OK "Created site: $BackendSite"
} else {
    Set-ItemProperty "IIS:\Sites\$BackendSite" physicalPath $BackendPath
    Set-ItemProperty "IIS:\Sites\$BackendSite" applicationPool $BackendPool
    Write-OK "Updated: $BackendSite"
}

# Remove any binding that points to stratapp.org (not api.) — safety check
$wrongBindings = Get-WebBinding -Name $BackendSite | Where-Object { $_.bindingInformation -match "stratapp\.org$" -and $_.bindingInformation -notmatch "api\." }
foreach ($b in $wrongBindings) {
    Remove-WebBinding -Name $BackendSite -BindingInformation $b.bindingInformation -Protocol $b.protocol
    Write-Warn "Removed incorrect binding: $($b.protocol) $($b.bindingInformation)"
}

# Add correct bindings for api.stratapp.org
$existingApiBindings = Get-WebBinding -Name $BackendSite
foreach ($proto in @("http", "https")) {
    $port = if ($proto -eq "https") { 443 } else { 80 }
    $info = "*:${port}:api.stratapp.org"
    if (-not ($existingApiBindings | Where-Object { $_.bindingInformation -eq $info })) {
        New-WebBinding -Name $BackendSite -Protocol $proto -Port $port -HostHeader "api.stratapp.org"
        Write-OK "Added binding: $proto $info"
    } else {
        Write-OK "Binding exists: $proto $info"
    }
}

# ── 4. Register FastCGI handler for the backend site ─────────────────────────
Write-Step "Registering FastCGI handler for $BackendSite"

$scriptProcessor = "${PythonExe}|${WfastcgiRunner}"

# Add to global FastCGI application list if not present
$existing = Get-WebConfiguration "system.webServer/fastCgi/application" | 
            Where-Object { $_.fullPath -eq $PythonExe -and $_.arguments -eq $WfastcgiRunner }
if (-not $existing) {
    Add-WebConfiguration "system.webServer/fastCgi" -Value @{
        fullPath  = $PythonExe
        arguments = $WfastcgiRunner
    }
    Write-OK "Registered FastCGI application"
} else {
    Write-OK "FastCGI application already registered"
}

# Set environment variables on FastCGI application
$envVars = @{
    WSGI_HANDLER                  = "run.app"
    PYTHONPATH                    = $BackendPath
    FLASK_ENV                     = "production"
    FLASK_DEBUG                   = "false"
    DATABASE_PROVIDER             = "sqlite"
    DATABASE_PATH                 = "${BackendPath}\instance\infra_assessment.db"
    SECRET_KEY                    = "Zxcvbnm@0806@1973"
    CORS_ORIGINS                  = "https://stratapp.org,https://www.stratapp.org,http://localhost:3000,http://localhost:3001"
    INCLUDE_LOCALHOST_CORS_ORIGINS = "true"
    UPLOAD_FOLDER                 = "${BackendPath}\uploads"
}

$appFilter = "system.webServer/fastCgi/application[@fullPath='${PythonExe}' and @arguments='${WfastcgiRunner}']/environmentVariables"
foreach ($kv in $envVars.GetEnumerator()) {
    $existing = Get-WebConfigurationProperty -Filter "$appFilter/environmentVariable[@name='$($kv.Key)']" -Name "value" -ErrorAction SilentlyContinue
    if ($null -eq $existing) {
        Add-WebConfiguration -Filter $appFilter -Value @{ name = $kv.Key; value = $kv.Value }
    } else {
        Set-WebConfigurationProperty -Filter "$appFilter/environmentVariable[@name='$($kv.Key)']" -Name "value" -Value $kv.Value
    }
    Write-OK "Env var: $($kv.Key)"
}

# ── 5. Restart app pools and sites ────────────────────────────────────────────
Write-Step "Restarting app pools and sites"
foreach ($pool in @($BackendPool, $FrontendPool)) {
    Stop-WebAppPool -Name $pool -ErrorAction SilentlyContinue
    Start-WebAppPool -Name $pool
    Write-OK "Restarted pool: $pool"
}
foreach ($site in @($BackendSite, $FrontendSite)) {
    Stop-Website -Name $site -ErrorAction SilentlyContinue
    Start-Website -Name $site
    Write-OK "Started site: $site"
}

# ── 6. Verify ─────────────────────────────────────────────────────────────────
Write-Step "Verifying health endpoint (waiting 3 seconds for pool warm-up)..."
Start-Sleep -Seconds 3
try {
    $resp = Invoke-WebRequest -Uri "https://api.stratapp.org/api/health" `
                              -Headers @{Origin="https://stratapp.org"} `
                              -UseBasicParsing -TimeoutSec 10
    Write-Host "  HTTP $($resp.StatusCode)" -ForegroundColor Green
    Write-Host "  Content-Type: $($resp.Headers['Content-Type'])" -ForegroundColor Green
    $acao = $resp.Headers['Access-Control-Allow-Origin']
    if ($acao) { Write-OK "CORS header: $acao" }
    else        { Write-Warn "CORS header still missing — check wfastcgi log at C:\Windows\Temp\wfastcgi_runner.log" }
} catch {
    Write-Warn "Health check failed: $_ — pool may still be starting, wait 10s and retry."
}

Write-Host "`n=== Done ===" -ForegroundColor Cyan
Write-Host "Frontend: https://stratapp.org     → $FrontendPath" -ForegroundColor Gray
Write-Host "Backend:  https://api.stratapp.org → $BackendPath (Flask via wfastcgi)" -ForegroundColor Gray
