@echo off
set FLASK_DEBUG=false
set FLASK_ENV=production
cd /d E:\techmaapprationalization\local_app_rationalization\backend
E:\techmaapprationalization\local_app_rationalization\backend\.venv\Scripts\python.exe run.py >> E:\flask_stdout.log 2>> E:\flask_stderr.log
