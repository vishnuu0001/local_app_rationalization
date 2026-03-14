@echo off
set FLASK_DEBUG=false
set FLASK_ENV=production
cd /d "%~dp0backend"
"%~dp0backend\.venv\Scripts\python.exe" run.py >> "%~dp0flask_stdout.log" 2>> "%~dp0flask_stderr.log"
