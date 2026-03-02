# fix_iis_wfastcgi.ps1 - Run once to register wfastcgi with IIS and restart it

$wfastcgiExe = "E:\techmaapprationalization\local_app_rationalization\backend\.venv\Scripts\wfastcgi-enable.exe"

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

# Step 2: Grant IIS app pool read/execute access to backend folder
$backendPath = "E:\techmaapprationalization\local_app_rationalization\backend"
Write-Host "`nGranting IIS AppPool\DefaultAppPool access to backend..." -ForegroundColor Cyan
icacls $backendPath /grant "IIS AppPool\DefaultAppPool:(OI)(CI)RX" /T | Out-Null
Write-Host "Permissions applied." -ForegroundColor Green

# Step 3: Restart IIS
Write-Host "`nRestarting IIS..." -ForegroundColor Cyan
iisreset

Write-Host "`nDone. Test https://api.stratapp.org/api/health in your browser." -ForegroundColor Green
pause
