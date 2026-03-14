#!/usr/bin/env python
"""Quick test to verify TraceabilityService works"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Initialize Flask app context
from app import create_app, db

app = create_app()

with app.app_context():
    from app.services.traceability_service import TraceabilityService
    
    print("✓ Service imported successfully")
    print("\nFetching traceability matrix...")
    
    result = TraceabilityService.get_traceability_matrix()
    
    print(f"\n✓ Traceability matrix generated!")
    print(f"  - Total Applications: {result['summary']['total_applications']}")
    print(f"  - Total Entries: {result['summary']['total_entries']}")
    print(f"  - Unique Infrastructure: {result['summary']['unique_infrastructure']}")
    print(f"  - Unique Capabilities: {result['summary']['unique_capabilities']}")
    print(f"  - Applications to Retain: {result['summary']['applications_to_retain']}")
    print(f"  - Applications to Migrate: {result['summary']['applications_to_migrate']}")
    print(f"  - Applications to Decommission: {result['summary']['applications_to_decommission']}")
    print(f"\nFirst 3 entries:")
    for i, entry in enumerate(result['matrix'][:3]):
        print(f"  {i+1}. {entry['application']} ({entry['capability']}) - {entry['action']}")
