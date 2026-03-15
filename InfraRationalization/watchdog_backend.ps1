# StratApp InfraScan Backend Watchdog
# Monitors the FastAPI backend on port 8083 and restarts it if it stops.
# Cloudflare remote config routes infra.stratapp.org -> http://127.0.0.1:8083
# FastAPI serves both the React SPA and /api/* on this port

$ProjectDir  = $PSScriptRoot
$PythonExe   = Join-Path $ProjectDir '.venv\Scripts\python.exe'
$LogFile     = 'E:\infrascan_stderr.log'
$StdoutFile  = 'E:\infrascan_stdout.log'
$CheckSecs   = 30

function Is-InfraScanRunning {
    $conn = Get-NetTCPConnection -LocalPort 8083 -State Listen -ErrorAction SilentlyContinue
    return ($null -ne $conn)
}

function Start-InfraScan {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName               = $PythonExe
    $psi.Arguments              = '-m uvicorn api.server:app --host 0.0.0.0 --port 8083'
    $psi.WorkingDirectory       = $ProjectDir
    $psi.UseShellExecute        = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    $psi.CreateNoWindow         = $true

    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi

    $stdoutAction = { Add-Content -Path $StdoutFile -Value $Event.SourceEventArgs.Data }
    $stderrAction = { Add-Content -Path $LogFile -Value $Event.SourceEventArgs.Data }
    Register-ObjectEvent -InputObject $proc -EventName OutputDataReceived -Action $stdoutAction | Out-Null
    Register-ObjectEvent -InputObject $proc -EventName ErrorDataReceived -Action $stderrAction | Out-Null

    $proc.Start() | Out-Null
    $proc.BeginOutputReadLine()
    $proc.BeginErrorReadLine()

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "[Watchdog $timestamp] InfraScan started (PID $($proc.Id))" | Add-Content $LogFile
    return $proc
}

$infraScanProc = $null
while ($true) {
    if (-not (Is-InfraScanRunning)) {
        $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        "[Watchdog $timestamp] Port 8083 not listening - starting InfraScan..." | Add-Content $LogFile

        $infraScanProc = Start-InfraScan
        Start-Sleep -Seconds 8
    }
    Start-Sleep -Seconds $CheckSecs
}
