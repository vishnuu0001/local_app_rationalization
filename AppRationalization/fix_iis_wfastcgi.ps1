# fix_iis_wfastcgi.ps1 - Run once to register wfastcgi with IIS and restart it

$BackendRoot = $PSScriptRoot
$wfastcgiExe = Join-Path $BackendRoot "backend\.venv\Scripts\wfastcgi-enable.exe"

# Compute absolute paths for web.config placeholders
$pythonExe    = Join-Path $BackendRoot "backend\.venv\Scripts\python.exe"
$wfastcgiApp  = Join-Path $BackendRoot "backend\wfastcgi_runner.py"
$webConfigPath = Join-Path $BackendRoot "backend\web.config"

# Check admin
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Not running as Administrator - relaunching elevated..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

Write-Host "Running as Administrator." -ForegroundColor Green

# Step 1: Register wfastcgi
if (Test-Path $wfastcgiExe) {
    Write-Host "`nRegistering wfastcgi with IIS..." -ForegroundColor Cyan
    & $wfastcgiExe
} else {
    Write-Error "wfastcgi-enable.exe not found at: $wfastcgiExe"
    Write-Host "Run: pip install wfastcgi   inside the venv first." -ForegroundColor Yellow
    pause
    exit 1
}

# Step 2: Write correct paths into web.config (replaces __BACKEND_PYTHON__ / __BACKEND_WFASTCGI__ tokens)
Write-Host "`nPatch web.config with resolved paths..." -ForegroundColor Cyan
if (Test-Path $webConfigPath) {
    $content = Get-Content $webConfigPath -Raw
    $content = $content -replace '__BACKEND_PYTHON__', $pythonExe.Replace('\', '\\')
    $content = $content -replace '__BACKEND_WFASTCGI__', $wfastcgiApp.Replace('\', '\\')
    Set-Content $webConfigPath $content -Encoding UTF8
    Write-OK "web.config updated: python=$pythonExe"
} else {
    Write-Host "    WARN: web.config not found at $webConfigPath" -ForegroundColor Yellow
}

# Step 3: Grant IIS app pool read/execute access to backend folder
$backendPath = Join-Path $BackendRoot "backend"
Write-Host "`nGranting IIS AppPool\DefaultAppPool access to backend..." -ForegroundColor Cyan
icacls $backendPath /grant "IIS AppPool\DefaultAppPool:(OI)(CI)RX" /T | Out-Null
Write-Host "Permissions applied." -ForegroundColor Green

# Step 4: Restart IIS
Write-Host "`nRestarting IIS..." -ForegroundColor Cyan
iisreset

Write-Host "`nDone. Test https://api.stratapp.org/api/health in your browser." -ForegroundColor Green
pause
