# StratApp Flask Backend Watchdog
# Monitors Flask on port 5000, restarts it if down.
# Runs forever - intended to be launched via scheduled task at logon.

$BackendDir  = Join-Path $PSScriptRoot 'backend'
$PythonExe   = "$BackendDir\.venv\Scripts\python.exe"
$RunScript   = "$BackendDir\run.py"
$LogFile     = 'E:\flask_stderr.log'
$StdoutFile  = 'E:\flask_stdout.log'
$CheckSecs   = 30   # how often to check (seconds)

function Is-FlaskRunning {
    $conn = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
    return ($null -ne $conn)
}

function Start-Flask {
    $env:FLASK_DEBUG = 'false'
    $env:FLASK_ENV   = 'production'

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName               = $PythonExe
    $psi.Arguments              = "`"$RunScript`""
    $psi.WorkingDirectory       = $BackendDir
    $psi.UseShellExecute        = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    $psi.CreateNoWindow         = $true

    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi

    # Async log stdout/stderr
    $stdoutAction = { Add-Content -Path $StdoutFile -Value $Event.SourceEventArgs.Data }
    $stderrAction = { Add-Content -Path $LogFile    -Value $Event.SourceEventArgs.Data }
    Register-ObjectEvent -InputObject $proc -EventName OutputDataReceived -Action $stdoutAction | Out-Null
    Register-ObjectEvent -InputObject $proc -EventName ErrorDataReceived  -Action $stderrAction | Out-Null

    $proc.Start()      | Out-Null
    $proc.BeginOutputReadLine()
    $proc.BeginErrorReadLine()

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "[Watchdog $timestamp] Flask started (PID $($proc.Id))" | Add-Content $LogFile
    return $proc
}

# Main watchdog loop
$flaskProc = $null
while ($true) {
    if (-not (Is-FlaskRunning)) {
        $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        "[Watchdog $timestamp] Port 5000 not listening — starting Flask..." | Add-Content $LogFile

        # Kill any zombie python processes to free the port
        Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2

        $flaskProc = Start-Flask
        Start-Sleep -Seconds 8   # wait for Flask to bind
    }
    Start-Sleep -Seconds $CheckSecs
}
