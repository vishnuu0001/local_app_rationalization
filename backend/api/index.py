"""
WSGI entry point for IIS (wfastcgi) and any WSGI-compatible server.
IIS FastCGI points wfastcgi at this file via WSGI_HANDLER=api.index.app,
or directly at run.app via wfastcgi_runner.py — either works.
"""
import sys
import os
from pathlib import Path

# Ensure backend root is on the path regardless of working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault('FLASK_ENV', 'production')

from app import create_app

app = create_app(config_name='production')
