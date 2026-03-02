Set objShell = CreateObject("WScript.Shell")
objShell.Run "powershell.exe -NonInteractive -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""E:\techmaapprationalization\local_app_rationalization\watchdog_backend.ps1""", 0, False
