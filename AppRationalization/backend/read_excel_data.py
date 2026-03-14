"""Script to read actual Excel data and identify server count"""
import pandas as pd
import os

data_dir = os.path.join(os.path.dirname(__file__), 'data')

# Read CORENT data
corent_file = os.path.join(data_dir, 'CORENTReport.xlsx')
print("=" * 80)
print("CORENT REPORT ANALYSIS")
print("=" * 80)

try:
    df_corent = pd.read_excel(corent_file)
    print(f"\nTotal CORENT records: {len(df_corent)}")
    print(f"Columns: {list(df_corent.columns)}\n")
    
    # Find server-related columns
    server_cols = [col for col in df_corent.columns if 'host' in col.lower() or 'server' in col.lower() or 'platform' in col.lower()]
    print(f"Server-related columns: {server_cols}")
    
    # Try to find app ID column
    app_id_cols = [col for col in df_corent.columns if 'app' in col.lower() or 'id' in col.lower()]
    print(f"App ID columns: {app_id_cols}\n")
    
    # Show first few rows
    print("First 5 CORENT records:")
    print(df_corent.head(5).to_string())
    
except Exception as e:
    print(f"Error reading CORENT file: {e}")

# Read CAST data
cast_file = os.path.join(data_dir, 'CASTReport.xlsx')
print("\n" + "=" * 80)
print("CAST REPORT ANALYSIS")
print("=" * 80)

try:
    df_cast = pd.read_excel(cast_file)
    print(f"\nTotal CAST records: {len(df_cast)}")
    print(f"Columns: {list(df_cast.columns)}\n")
    
    # Find app ID column
    app_id_cols = [col for col in df_cast.columns if 'app' in col.lower() or 'id' in col.lower()]
    print(f"App ID columns: {app_id_cols}\n")
    
    # Show first few rows
    print("First 5 CAST records:")
    print(df_cast.head(5).to_string())
    
except Exception as e:
    print(f"Error reading CAST file: {e}")
