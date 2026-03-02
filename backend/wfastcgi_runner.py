"""
wfastcgi wrapper - sets all required environment variables before starting wfastcgi.
IIS scriptProcessor points to this file instead of wfastcgi.py directly.
"""
import os
import sys
import traceback

LOG_PATH = r'C:\Windows\Temp\wfastcgi_runner.log'

def log(msg):
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            import datetime
            f.write(f"[{datetime.datetime.now()}] {msg}\n")
    except Exception:
        pass

try:
    log("wfastcgi_runner starting")

    # Ensure backend is on the path
    BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BACKEND_DIR)
    log(f"BACKEND_DIR: {BACKEND_DIR}")

    # Set required env vars (only if not already set)
    os.environ.setdefault('WSGI_HANDLER', 'run.app')
    os.environ.setdefault('PYTHONPATH', BACKEND_DIR)
    os.environ.setdefault('FLASK_ENV', 'production')
    os.environ.setdefault('FLASK_DEBUG', 'false')
    os.environ.setdefault('DATABASE_PROVIDER', 'sqlite')
    os.environ.setdefault('DATABASE_PATH', os.path.join(BACKEND_DIR, 'instance', 'infra_assessment.db'))
    os.environ.setdefault('SECRET_KEY', 'Zxcvbnm@0806@1973')
    os.environ.setdefault('CORS_ORIGINS', 'https://stratapp.org,https://www.stratapp.org,http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001')
    os.environ.setdefault('INCLUDE_LOCALHOST_CORS_ORIGINS', 'true')

    # Ensure instance dir exists and is writable
    instance_dir = os.path.join(BACKEND_DIR, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    log(f"instance_dir: {instance_dir}")

    # Hand off to wfastcgi
    wfastcgi_path = os.path.join(BACKEND_DIR, '.venv', 'Lib', 'site-packages', 'wfastcgi.py')
    log(f"loading wfastcgi from: {wfastcgi_path}")
    with open(wfastcgi_path) as f:
        exec(compile(f.read(), wfastcgi_path, 'exec'))

except Exception as e:
    log(f"FATAL ERROR: {e}\n{traceback.format_exc()}")
    raise
