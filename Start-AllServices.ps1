[CmdletBinding()]
param(
    [switch]$InstallDeps,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Message)
    Write-Host "[start-all] $Message" -ForegroundColor Cyan
}

function Assert-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}

function Ensure-Directory {
    param([string]$Path, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label directory not found: $Path"
    }
}

function Invoke-InDirectory {
    param(
        [string]$Directory,
        [scriptblock]$ScriptBlock
    )

    Push-Location -LiteralPath $Directory
    try {
        & $ScriptBlock
    }
    finally {
        Pop-Location
    }
}

function Ensure-PythonEnv {
    param(
        [string]$ProjectDir,
        [switch]$ForceInstall,
        [switch]$IsDryRun
    )

    $venvPython = Join-Path $ProjectDir '.venv\Scripts\python.exe'

    if ($IsDryRun) {
        if (Test-Path -LiteralPath $venvPython) {
            return $venvPython
        }
        return 'python'
    }

    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Step "Creating virtual environment in $ProjectDir"
        Invoke-InDirectory -Directory $ProjectDir -ScriptBlock {
            python -m venv .venv
        }
        $ForceInstall = $true
    }

    if ($ForceInstall) {
        $requirements = Join-Path $ProjectDir 'requirements.txt'
        if (Test-Path -LiteralPath $requirements) {
            Write-Step "Installing Python dependencies in $ProjectDir"
            & $venvPython -m pip install --upgrade pip
            & $venvPython -m pip install -r $requirements
        }
    }

    return $venvPython
}

function Ensure-NodeModules {
    param(
        [string]$ProjectDir,
        [switch]$ForceInstall,
        [switch]$IsDryRun
    )

    if ($IsDryRun) {
        return
    }

    $modulesPath = Join-Path $ProjectDir 'node_modules'
    if ($ForceInstall -or -not (Test-Path -LiteralPath $modulesPath)) {
        Write-Step "Installing Node dependencies in $ProjectDir"
        Invoke-InDirectory -Directory $ProjectDir -ScriptBlock {
            npm install
        }
    }
}

function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$Directory,
        [string]$Command,
        [switch]$IsDryRun
    )

    if ($IsDryRun) {
        Write-Host "DRY-RUN: [$Title] $Command" -ForegroundColor Yellow
        return
    }

    $safeTitle = $Title.Replace("'", "''")
    $safeDirectory = $Directory.Replace("'", "''")

    $payload = @"
`$Host.UI.RawUI.WindowTitle = '$safeTitle'
Set-Location -LiteralPath '$safeDirectory'
Write-Host '[$safeTitle] Starting in $safeDirectory' -ForegroundColor Green
$Command
if (`$LASTEXITCODE -ne `$null -and `$LASTEXITCODE -ne 0) {
    Write-Host '[$safeTitle] Exited with code' `$LASTEXITCODE -ForegroundColor Red
}
"@

    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($payload))
    Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy',
        'Bypass',
        '-EncodedCommand',
        $encoded
    ) | Out-Null
}

$repoRoot = Split-Path -Parent $PSCommandPath

$appRBackendDir = Join-Path $repoRoot 'AppRationalization\backend'
$appRFrontendDir = Join-Path $repoRoot 'AppRationalization\frontend'
$codeBackendDir = Join-Path $repoRoot 'CodeAnalysis'
$codeFrontendDir = Join-Path $repoRoot 'CodeAnalysis\frontend'
$infraBackendDir = Join-Path $repoRoot 'InfraRationalization'
$infraFrontendDir = Join-Path $repoRoot 'InfraRationalization\frontend'

Ensure-Directory -Path $appRBackendDir -Label 'AppRationalization backend'
Ensure-Directory -Path $appRFrontendDir -Label 'AppRationalization frontend'
Ensure-Directory -Path $codeBackendDir -Label 'CodeAnalysis backend'
Ensure-Directory -Path $codeFrontendDir -Label 'CodeAnalysis frontend'
Ensure-Directory -Path $infraBackendDir -Label 'InfraRationalization backend'
Ensure-Directory -Path $infraFrontendDir -Label 'InfraRationalization frontend'

Assert-Command -Name 'python'
Assert-Command -Name 'npm'

$appREnv  = Join-Path $appRBackendDir '.env'
$codeEnv  = Join-Path $codeBackendDir '.env'
$infraEnv = Join-Path $infraBackendDir '.env'

if (-not (Test-Path -LiteralPath $appREnv)) {
    Write-Warning "Missing .env file: $appREnv"
}
if (-not (Test-Path -LiteralPath $codeEnv)) {
    Write-Warning "Missing .env file: $codeEnv"
}
if (-not (Test-Path -LiteralPath $infraEnv)) {
    Write-Warning "Missing .env file: $infraEnv"
}

$appRPython  = Ensure-PythonEnv -ProjectDir $appRBackendDir -ForceInstall:$InstallDeps -IsDryRun:$DryRun
$codePython  = Ensure-PythonEnv -ProjectDir $codeBackendDir -ForceInstall:$InstallDeps -IsDryRun:$DryRun
$infraPython = Ensure-PythonEnv -ProjectDir $infraBackendDir -ForceInstall:$InstallDeps -IsDryRun:$DryRun

Ensure-NodeModules -ProjectDir $appRFrontendDir -ForceInstall:$InstallDeps -IsDryRun:$DryRun
Ensure-NodeModules -ProjectDir $codeFrontendDir -ForceInstall:$InstallDeps -IsDryRun:$DryRun
Ensure-NodeModules -ProjectDir $infraFrontendDir -ForceInstall:$InstallDeps -IsDryRun:$DryRun

$appRBackendCommand  = "& '$appRPython' run.py"
$appRFrontendCommand  = 'npm start'
$codeBackendCommand  = "& '$codePython' -m uvicorn api.server:app --host 0.0.0.0 --port 8082"
$codeFrontendCommand  = 'npm run dev'
$infraBackendCommand  = "& '$infraPython' -m uvicorn api.server:app --host 0.0.0.0 --port 8083"
$infraFrontendCommand = 'npm run dev'

Start-ServiceWindow -Title 'AppRationalization Backend' -Directory $appRBackendDir -Command $appRBackendCommand -IsDryRun:$DryRun
Start-Sleep -Milliseconds 400
Start-ServiceWindow -Title 'AppRationalization Frontend' -Directory $appRFrontendDir -Command $appRFrontendCommand -IsDryRun:$DryRun
Start-Sleep -Milliseconds 400
Start-ServiceWindow -Title 'CodeAnalysis Backend (port 8082)' -Directory $codeBackendDir -Command $codeBackendCommand -IsDryRun:$DryRun
Start-Sleep -Milliseconds 400
Start-ServiceWindow -Title 'CodeAnalysis Frontend' -Directory $codeFrontendDir -Command $codeFrontendCommand -IsDryRun:$DryRun
Start-Sleep -Milliseconds 400
Start-ServiceWindow -Title 'InfraRationalization Backend (port 8083)' -Directory $infraBackendDir -Command $infraBackendCommand -IsDryRun:$DryRun
Start-Sleep -Milliseconds 400
Start-ServiceWindow -Title 'InfraRationalization Frontend' -Directory $infraFrontendDir -Command $infraFrontendCommand -IsDryRun:$DryRun

Write-Host ''
Write-Host 'Launch complete.' -ForegroundColor Green
Write-Host 'AppRationalization Portal: http://localhost:3000/login'
Write-Host 'CodeAnalysis UI:          http://localhost:5173  (production: https://code.stratapp.org)'
Write-Host 'InfraRationalization UI:  http://localhost:5174  (production: https://infra.stratapp.org)'
Write-Host ''
Write-Host 'Usage:' -ForegroundColor Cyan
Write-Host '  .\Start-AllServices.ps1'
Write-Host '  .\Start-AllServices.ps1 -InstallDeps    # optional dependency refresh'
Write-Host '  .\Start-AllServices.ps1 -DryRun         # print commands only'