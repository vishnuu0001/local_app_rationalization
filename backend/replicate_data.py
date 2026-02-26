#!/usr/bin/env python
"""
Script to replicate IndustryData records to CorentData and CASTData
for unified correlation across all three data sources
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.industry_data import IndustryData
from app.models.corent_data import CorentData
from app.models.cast import CASTData

def replicate_industry_data_to_all_sources():
    """Replicate IndustryData records to CorentData and CASTData"""
    app = create_app('development')
    
    with app.app_context():
        print("[*] Starting data replication...\n")
        
        # Get all IndustryData records
        industry_items = IndustryData.query.all()
        print(f"[*] Found {len(industry_items)} IndustryData records")
        
        # Clear existing CorentData and CASTData
        print("[*] Clearing existing CorentData and CASTData...")
        CorentData.query.delete()
        CASTData.query.delete()
        db.session.commit()
        print("[OK] Cleared old data\n")
        
        # Replicate to CorentData
        print("[*] Replicating to CorentData...")
        corent_records = []
        for ind in industry_items:
            corent = CorentData(
                app_id=ind.app_id,
                app_name=ind.app_name,
                architecture_type=getattr(ind, 'architecture_type', None),
                business_owner=getattr(ind, 'business_owner', None),
                platform_host=getattr(ind, 'platform_host', None),
                server_type=getattr(ind, 'application_type', None),  # Map application_type to server_type
                operating_system='Unknown',
                environment=getattr(ind, 'environment', None) or 'Production',
                cloud_suitability=getattr(ind, 'cloud_suitability', None),
                volume_external_dependencies='0'
            )
            corent_records.append(corent)
        
        db.session.add_all(corent_records)
        db.session.commit()
        print(f"[OK] Created {len(corent_records)} CorentData records\n")
        
        # Replicate to CASTData
        print("[*] Replicating to CASTData...")
        cast_records = []
        for ind in industry_items:
            cast = CASTData(
                app_id=ind.app_id,
                app_name=ind.app_name,
                application_architecture=getattr(ind, 'architecture_type', 'N-tier'),
                source_code_availability='Unknown',
                programming_language='Unknown',
                component_coupling='0.0',
                cloud_suitability=getattr(ind, 'cloud_suitability', None) or 'Unknown',
                volume_external_dependencies='0',
                code_design='Unknown'
            )
            cast_records.append(cast)
        
        db.session.add_all(cast_records)
        db.session.commit()
        print(f"[OK] Created {len(cast_records)} CASTData records\n")
        
        # Verify counts
        ind_count = IndustryData.query.count()
        corent_count = CorentData.query.count()
        cast_count = CASTData.query.count()
        
        print("=== FINAL RECORD COUNTS ===")
        print(f"IndustryData: {ind_count} records")
        print(f"CorentData: {corent_count} records")
        print(f"CASTData: {cast_count} records")
        print(f"TOTAL: {ind_count + corent_count + cast_count} records")
        
        if ind_count == corent_count == cast_count == len(industry_items):
            print("\n[✓] SUCCESS - All three databases now have the same 195 records!")
            return True
        else:
            print("\n[✗] ERROR - Record counts don't match!")
            return False

if __name__ == '__main__':
    success = replicate_industry_data_to_all_sources()
    sys.exit(0 if success else 1)
