"""Load Excel production data into database"""
from app import db, create_app
from app.services.excel_data_loader_service import ExcelDataLoaderService

app = create_app()
with app.app_context():
    print("=" * 80)
    print("LOADING EXCEL PRODUCTION DATA")
    print("=" * 80)
    
    result = ExcelDataLoaderService.load_all_data()
    
    print("\n" + "=" * 80)
    print("LOAD COMPLETE")
    print("=" * 80)
    print(f"CORENT Records Loaded: {result['corent_loaded']}")
    print(f"CAST Records Loaded: {result['cast_loaded']}")
    print(f"TOTAL Records Loaded: {result['total']}")
    print("=" * 80)
