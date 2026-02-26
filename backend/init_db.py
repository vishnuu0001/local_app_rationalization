#!/usr/bin/env python
"""
Database initialization script - Creates database schema and loads test data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.services.data_initialization_service import DataInitializationService

def init_database():
    """Initialize database with schema and test data for CorentData and CASTData"""
    app = create_app('development')
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("[OK] Database tables created")
        
        # Load test data for CorentData and CASTData (but not IndustryData - user uploads that)
        try:
            DataInitializationService.initialize_test_data()
            print("[OK] Test data loaded for CorentData and CASTData")
        except Exception as e:
            print(f"[WARNING] Could not load test data: {e}")
        
        print("\n[OK] Database initialization complete!")
        print("\nNext steps:")
        print("  1. Start the backend: python run.py")
        print("  2. Upload your data files:")
        print("     - Corent Reports via Infrastructure Uploads")
        print("     - CAST Analysis via Code Uploads")
        print("     - Industry Templates via Industry Templates Uploads")
        print("  3. Navigate to the dashboard at http://localhost:3002")
        print("  4. Click 'Run Correlation' to link infrastructure and code data")

if __name__ == '__main__':
    init_database()
