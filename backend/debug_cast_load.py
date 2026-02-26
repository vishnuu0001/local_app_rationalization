"""Debug CAST data loading"""
from app import db, create_app
from app.services.excel_data_loader_service import ExcelDataLoaderService
import traceback

app = create_app()
with app.app_context():
    print("Testing CAST data load...")
    try:
        count = ExcelDataLoaderService._load_cast_data()
        print(f"CAST records loaded: {count}")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
