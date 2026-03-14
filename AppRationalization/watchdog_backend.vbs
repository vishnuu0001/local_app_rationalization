Set objShell = CreateObject("WScript.Shell")
Dim scriptDir
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)
objShell.Run "powershell.exe -NonInteractive -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptDir & "\watchdog_backend.ps1""", 0, False
