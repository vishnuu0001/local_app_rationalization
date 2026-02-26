"""
Vercel Serverless Function Handler
This file exports the Flask application for Vercel deployment with automatic database selection
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure production environment for Vercel
os.environ.setdefault('FLASK_ENV', 'production')

from app import create_app, db

# Create Flask application with production config
app = create_app(config_name='production')

# Export for Vercel
handler = app
