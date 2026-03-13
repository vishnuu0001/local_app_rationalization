"""
Excel Data Loader Service - Loads actual production data from Excel reports

This service reads CORENT and CAST Excel files and populates the database
with the complete set of real application data.
"""

import os
import pandas as pd
from app import db
from app.models.corent_data import CorentData
from app.models.cast import CASTData


class ExcelDataLoaderService:
    """Service to load production data from Excel files"""
    
    @staticmethod
    def load_all_data():
        """Load both CORENT and CAST data from Excel files"""
        print("Loading CORENT data from Excel...")
        corent_count = ExcelDataLoaderService._load_corent_data()
        
        print("Loading CAST data from Excel...")
        cast_count = ExcelDataLoaderService._load_cast_data()
        
        return {
            'corent_loaded': corent_count,
            'cast_loaded': cast_count,
            'total': corent_count + cast_count
        }
    
    @staticmethod
    def _load_corent_data():
        """Load CORENT infrastructure data from Excel"""
        try:
            # Clear existing data
            db.session.query(CorentData).delete()
            db.session.commit()
            
            # Read Excel file
            excel_path = os.path.join(
                os.path.dirname(__file__), 
                '..', '..', 'data', 'CORENTReport.xlsx'
            )
            
            df = pd.read_excel(excel_path)
            
            # Column mapping from Excel to database model
            column_mapping = {
                'ArchitectureType': 'architecture_type',
                'BusinessOwner': 'business_owner',
                'PlatformHost': 'platform_host',
                'Server Type': 'server_type',
                'Server IP': 'server_ip',
                'SERVER_IP': 'server_ip',
                'IP Address': 'server_ip',
                'Server Name': 'server_name',
                'SERVER_NAME': 'server_name',
                'Operating System': 'operating_system',
                'CPU Core': 'cpu_core',
                'Memory': 'memory',
                'Internal Storage': 'internal_storage',
                'External Storage': 'external_storage',
                'Storage Type': 'storage_type',
                'DB Storage': 'db_storage',
                'DB Engine': 'db_engine',
                'Environment': 'environment',
                'INSTALL TYPE': 'install_type',
                'Virtualization Attributes': 'virtualization_attributes',
                'Compute / Server Hardware Architecture': 'compute_server_hardware_architecture',
                'Application Stability': 'application_stability',
                'Virtualization State': 'virtualization_state',
                'Storage Decomposition': 'storage_decomposition',
                'FLASH Storage Used': 'flash_storage_used',
                'CPU Requirement': 'cpu_requirement',
                'Memory (RAM) Requirement': 'memory_ram_requirement',
                'Mainframe Dependency': 'mainframe_dependency',
                'Desktop Dependency': 'desktop_dependency',
                'App OS / Platform Cloud Suitability': 'app_os_platform_cloud_suitability',
                'Database Cloud Readiness': 'database_cloud_readiness',
                'Integration Middleware Cloud Readiness': 'integration_middleware_cloud_readiness',
                'Application Hardware dependency': 'application_hardware_dependency',
                'App COTS vs. Non-COTS Only': 'app_cots_vs_non_cots',
                'Cloud Suitability': 'cloud_suitability',
                'Volume of External Dependencies': 'volume_external_dependencies',
                'App Load Predictability / Elasticity': 'app_load_predictability_elasticity',
                'Financially Optimizable Hardware Usage': 'financially_optimizable_hardware_usage',
                'Distributed Architecture Design or not': 'distributed_architecture_design',
                'Latency Requirements': 'latency_requirements',
                'Ubiquitous Access Requirements': 'ubiquitous_access_requirements',
                'No. of Production Environments': 'no_production_environments',
                'No. of Non-Production Environments': 'no_non_production_environments',
                'HA/DR Requirements': 'ha_dr_requirements',
                'RTO Requirements': 'rto_requirements',
                'RPO Requirements': 'rpo_requirements',
                'Deployment Geography': 'deployment_geography'
            }
            
            # Load records
            count = 0
            for idx, row in df.iterrows():
                corent_record = {}
                
                for excel_col, db_field in column_mapping.items():
                    if excel_col in df.columns:
                        value = row[excel_col]
                        
                        # Handle NaN values
                        if pd.isna(value):
                            value = None
                        
                        # Handle string fields
                        if isinstance(value, str):
                            value = value.strip() if value else None
                        
                        corent_record[db_field] = value
                
                # Create and add record
                if corent_record:
                    corent_obj = CorentData(**corent_record)
                    db.session.add(corent_obj)
                    count += 1
            
            db.session.commit()
            print(f"[OK] Loaded {count} CORENT records")
            return count
            
        except Exception as e:
            print(f"[ERROR] Error loading CORENT data: {e}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def _load_cast_data():
        """Load CAST code analysis data from Excel"""
        try:
            # Clear existing data
            db.session.query(CASTData).delete()
            db.session.commit()
            
            # Read Excel file
            excel_path = os.path.join(
                os.path.dirname(__file__), 
                '..', '..', 'data', 'CASTReport.xlsx'
            )
            
            df = pd.read_excel(excel_path)
            
            # Column mapping from Excel to database model
            column_mapping = {
                'APP ID': 'app_id',
                'APP NAME': 'app_name',
                'REPO NAME': 'repo_name',
                'Repo Name': 'repo_name',
                'REPO': 'repo_name',
                'Repo': 'repo_name',
                'SERVER NAME': 'server_name',
                'Server Name': 'server_name',
                'SERVER_NAME': 'server_name',
                'Application Architecture': 'application_architecture',
                'Source Code Availability': 'source_code_availability',
                'Programming Language': 'programming_language',
                'Component Coupling': 'component_coupling',
                'Cloud Suitability': 'cloud_suitability',
                'Volume of External Dependencies': 'volume_external_dependencies',
                'App Service / API Readiness': 'app_service_api_readiness',
                'Degree of Code Protocols': 'degree_of_code_protocols',
                'Code Design': 'code_design',
                'Application-Code Complexity / Volume': 'application_code_complexity_volume',
                'Distributed Architecture Design or not': 'distributed_architecture_design',
                'Application Type': 'application_type',
            }
            
            # Load records
            count = 0
            for idx, row in df.iterrows():
                cast_record = {}
                
                for excel_col, db_field in column_mapping.items():
                    if excel_col in df.columns:
                        value = row[excel_col]
                        
                        # Handle NaN values
                        if pd.isna(value):
                            value = None
                        
                        # Handle string fields
                        if isinstance(value, str):
                            value = value.strip() if value else None
                        
                        cast_record[db_field] = value
                
                # Create and add record
                if cast_record.get('app_id'):
                    cast_record['app_id'] = str(cast_record['app_id']).strip()
                    cast_obj = CASTData(**cast_record)
                    db.session.add(cast_obj)
                    count += 1
            
            db.session.commit()
            print(f"[OK] Loaded {count} CAST records")
            return count
            
        except Exception as e:
            print(f"[ERROR] Error loading CAST data: {e}")
            db.session.rollback()
            return 0
