# fix_iis_wfastcgi.ps1 - Run once to register wfastcgi with IIS and restart it

$BackendRoot = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($BackendRoot)) {
    $BackendRoot = (Get-Location).Path
}

# Allow launching from either AppRationalization root or backend folder.
if ((Split-Path -Leaf $BackendRoot).ToLowerInvariant() -eq "backend") {
    $BackendRoot = Split-Path -Parent $BackendRoot
}

$backendPath = Join-Path $BackendRoot "backend"
if (-not (Test-Path $backendPath)) {
    Write-Error "Could not find backend folder under: $BackendRoot"
    Write-Host "Run this script from AppRationalization root or backend folder." -ForegroundColor Yellow
    exit 1
}

$wfastcgiExe = Join-Path $backendPath ".venv\Scripts\wfastcgi-enable.exe"
$wfastcgiPy = Join-Path $backendPath ".venv\Lib\site-packages\wfastcgi.py"
$appCmdExe = Join-Path $env:WINDIR "System32\inetsrv\appcmd.exe"

# Compute absolute paths for web.config placeholders
$pythonExe    = Join-Path $backendPath ".venv\Scripts\python.exe"
$wfastcgiApp  = Join-Path $backendPath "wfastcgi_runner.py"
$webConfigPath = Join-Path $backendPath "web.config"

# Check admin
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Not running as Administrator - relaunching elevated..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

Write-Host "Running as Administrator." -ForegroundColor Green

# Step 1: Register wfastcgi
if (-not (Test-Path $pythonExe)) {
    Write-Error "python.exe not found at: $pythonExe"
    pause
    exit 1
}

Write-Host "`nRegistering wfastcgi with IIS..." -ForegroundColor Cyan

if (-not (Test-Path $wfastcgiPy)) {
    Write-Host "wfastcgi.py not found. Repairing wfastcgi package..." -ForegroundColor Yellow
    & $pythonExe -m pip install --upgrade --force-reinstall wfastcgi
}

if (-not (Test-Path $wfastcgiPy)) {
    Write-Error "wfastcgi.py still missing at: $wfastcgiPy"
    pause
    exit 1
}

if (-not (Test-Path $appCmdExe)) {
    Write-Error "appcmd.exe not found at: $appCmdExe"
    pause
    exit 1
}

# Register the standard python.exe|...\wfastcgi.py pair expected by IIS + wfastcgi.
# Step 1a: Remove any existing entry so we start clean.
& $appCmdExe set config /section:system.webServer/fastCGI "/-[fullPath='$pythonExe',arguments='$wfastcgiPy']" 2>$null | Out-Null

# Step 1b: Add the entry with only the attributes IIS schema guarantees to accept.
& $appCmdExe set config /section:system.webServer/fastCGI "/+[fullPath='$pythonExe',arguments='$wfastcgiPy',signalBeforeTerminateSeconds='30']" | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Error "wfastcgi registration failed. Exit code: $LASTEXITCODE"
    pause
    exit 1
}

# Step 1c: Set timeout attributes one at a time so a bad value fails gracefully.
Write-Host "`nSetting FastCGI timeouts..." -ForegroundColor Cyan

# idleTimeout: seconds before IIS kills an idle process. 0 = never kill (fixes 502 after 5-min idle).
$r = & $appCmdExe set config /section:system.webServer/fastCGI "/[fullPath='$pythonExe',arguments='$wfastcgiPy'].idleTimeout:0" 2>&1
if ($LASTEXITCODE -eq 0) { Write-Host "    idleTimeout=0 (disabled)" -ForegroundColor Green } else { Write-Host "    idleTimeout: $r" -ForegroundColor Yellow }

# activityTimeout: max seconds a running request can be inactive.
$r = & $appCmdExe set config /section:system.webServer/fastCGI "/[fullPath='$pythonExe',arguments='$wfastcgiPy'].activityTimeout:3600" 2>&1
if ($LASTEXITCODE -eq 0) { Write-Host "    activityTimeout=3600" -ForegroundColor Green } else { Write-Host "    activityTimeout: $r" -ForegroundColor Yellow }

# requestTimeout: max total seconds per request.
$r = & $appCmdExe set config /section:system.webServer/fastCGI "/[fullPath='$pythonExe',arguments='$wfastcgiPy'].requestTimeout:90" 2>&1
if ($LASTEXITCODE -eq 0) { Write-Host "    requestTimeout=90" -ForegroundColor Green } else { Write-Host "    requestTimeout: $r" -ForegroundColor Yellow }

# maxInstances: allow up to 4 concurrent wfastcgi workers.
$r = & $appCmdExe set config /section:system.webServer/fastCGI "/[fullPath='$pythonExe',arguments='$wfastcgiPy'].maxInstances:4" 2>&1
if ($LASTEXITCODE -eq 0) { Write-Host "    maxInstances=4" -ForegroundColor Green } else { Write-Host "    maxInstances: $r" -ForegroundColor Yellow }

# Step 2: Write correct paths into web.config (replaces __BACKEND_PYTHON__ / __BACKEND_WFASTCGI__ tokens)
Write-Host "`nPatch web.config with resolved paths..." -ForegroundColor Cyan
if (Test-Path $webConfigPath) {
    $content = Get-Content $webConfigPath -Raw
    $content = $content.Replace('__BACKEND_PYTHON__', $pythonExe)
    $content = $content.Replace('__BACKEND_WFASTCGI__', $wfastcgiApp)

    # Keep scriptProcessor in exact FastCGI match form: C:\...\python.exe|C:\...\wfastcgi.py
    $scriptProcessorValue = "scriptProcessor=`"$pythonExe|$wfastcgiPy`""
    $content = [regex]::Replace($content, 'scriptProcessor="[^"]+"', $scriptProcessorValue, 1)

    Set-Content $webConfigPath $content -Encoding UTF8
    Write-Host "web.config updated: python=$pythonExe" -ForegroundColor Green
} else {
    Write-Host "    WARN: web.config not found at $webConfigPath" -ForegroundColor Yellow
}

# Step 3: Grant IIS app pool read/execute access to backend folder
Write-Host "`nGranting IIS app pool identities access to backend..." -ForegroundColor Cyan
icacls $backendPath /grant "IIS AppPool\AppRationalizationPool:(OI)(CI)RX" /T | Out-Null
icacls $backendPath /grant "IIS AppPool\DefaultAppPool:(OI)(CI)RX" /T | Out-Null

# If this venv is chained to a user/profile Python install, grant RX there too.
$pyvenvCfgPath = Join-Path $backendPath ".venv\pyvenv.cfg"
if (Test-Path $pyvenvCfgPath) {
    $pyvenvCfg = Get-Content $pyvenvCfgPath

    $homeLine = $pyvenvCfg | Where-Object { $_ -match '^home\s*=\s*' } | Select-Object -First 1
    if ($homeLine) {
        $pythonHome = ($homeLine -split '=', 2)[1].Trim()
        if (Test-Path $pythonHome) {
            Write-Host "Granting RX on Python home: $pythonHome" -ForegroundColor Cyan
            icacls $pythonHome /grant "IIS AppPool\AppRationalizationPool:(OI)(CI)RX" /T | Out-Null
        }
    }

    $exeLine = $pyvenvCfg | Where-Object { $_ -match '^executable\s*=\s*' } | Select-Object -First 1
    if ($exeLine) {
        $baseExe = ($exeLine -split '=', 2)[1].Trim()
        if (Test-Path $baseExe) {
            $baseVenvRoot = Split-Path (Split-Path $baseExe -Parent) -Parent
            if (Test-Path $baseVenvRoot) {
                Write-Host "Granting RX on base venv root: $baseVenvRoot" -ForegroundColor Cyan
                icacls $baseVenvRoot /grant "IIS AppPool\AppRationalizationPool:(OI)(CI)RX" /T | Out-Null
            }
        }
    }
}

Write-Host "Permissions applied." -ForegroundColor Green

# Step 4: Free port 8001 so CodeAnalysisUI site can bind on restart
Write-Host "`nChecking port 8001 for conflicting processes..." -ForegroundColor Cyan
$port8001 = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
if ($port8001) {
    foreach ($conn in $port8001) {
        $pid8001 = $conn.OwningProcess
        $proc = Get-Process -Id $pid8001 -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "    Killing $($proc.ProcessName) (PID $pid8001) holding port 8001..." -ForegroundColor Yellow
            Stop-Process -Id $pid8001 -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }
    Write-Host "    Port 8001 freed." -ForegroundColor Green
} else {
    Write-Host "    Port 8001 is free." -ForegroundColor Green
}

# Step 5: Restart IIS
Write-Host "`nRestarting IIS..." -ForegroundColor Cyan
iisreset

# Step 6: Explicitly start CodeAnalysisUI if still stopped after iisreset
Write-Host "`nEnsuring CodeAnalysisUI site is started..." -ForegroundColor Cyan
$siteState = & $appCmdExe list site /name:"CodeAnalysisUI" 2>$null
if ($siteState -match 'state:Stopped') {
    & $appCmdExe start site /site.name:"CodeAnalysisUI" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    CodeAnalysisUI started." -ForegroundColor Green
    } else {
        Write-Host "    Could not start CodeAnalysisUI - check bindings/port." -ForegroundColor Red
    }
} else {
    Write-Host "    CodeAnalysisUI is running." -ForegroundColor Green
}

Write-Host "`nDone. Test https://api.stratapp.org/api/health in your browser." -ForegroundColor Green
Write-Host "      https://code.stratapp.org to verify CodeAnalysisUI." -ForegroundColor Green
pause
