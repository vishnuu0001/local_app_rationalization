#!/usr/bin/env python
"""Quick verification that all three databases have 195 records"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.industry_data import IndustryData
from app.models.corent_data import CorentData
from app.models.cast import CASTData

app = create_app('development')
with app.app_context():
    ind_count = IndustryData.query.count()
    cor_count = CorentData.query.count()
    cas_count = CASTData.query.count()
    
    print('\n=== DATABASE VERIFICATION ===\n')
    print(f'IndustryData:  {ind_count:3d} records  {"OK" if ind_count == 195 else "FAIL"}')
    print(f'CorentData:    {cor_count:3d} records  {"OK" if cor_count == 195 else "FAIL"}')
    print(f'CASTData:      {cas_count:3d} records  {"OK" if cas_count == 195 else "FAIL"}')
    print(f'\nTOTAL:         {ind_count + cor_count + cas_count:3d} records\n')
    
    if ind_count == cor_count == cas_count == 195:
        print('Status: SUCCESS - All three databases synchronized with 195 records each!\n')
    else:
        print('Status: MISMATCH - Record counts are not equal!\n')
