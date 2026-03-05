"""Service for extracting CAST data and populating CASTData table"""

import logging
import json
import pandas as pd
from app import db
from app.models.cast import CASTData

logger = logging.getLogger(__name__)

class CASTDataService:
    """Service to extract CAST analysis data and store in CASTData table"""
    
    @staticmethod
    def populate_from_cast_analysis(extraction_result):
        """
        Extract and populate CASTData from CAST analysis extraction result
        
        Args:
            extraction_result: Dictionary with extracted CAST data containing:
                - application_inventory: List of ApplicationInventory records
                - application_classifications: List of ApplicationClassification records
                
        Returns:
            int: Number of records created/updated
        """
        try:
            records_created = 0
            
            # Extract from application inventory and combine with classifications
            app_inventory = extraction_result.get('application_inventory', [])
            
            if app_inventory:
                for app_record in app_inventory:
                    # Convert model object to dict if needed
                    if hasattr(app_record, 'to_dict'):
                        app_data = app_record.to_dict()
                    else:
                        app_data = app_record if isinstance(app_record, dict) else {}
                    
                    app_id = app_data.get('app_id', '').strip()
                    if not app_id:
                        logger.warning("[CASTData] Skipping record without app_id")
                        continue
                    
                    # Get or create CASTData record
                    cast_record = CASTData.query.filter_by(app_id=app_id).first()
                    
                    if not cast_record:
                        cast_record = CASTData(
                            app_id=app_id,
                            app_name=app_data.get('application', '')
                        )
                        db.session.add(cast_record)
                        records_created += 1
                    else:
                        cast_record.app_name = app_data.get('application', cast_record.app_name)
                    
                    # Populate fields from inventory data
                    cast_record.programming_language = app_data.get('primary_language')
                    # NOTE: application_type removed - now sourced from CorentData/IndustryData
                    cast_record.repo_name = app_data.get('repo', '') or ''
                    cast_record.source_code_availability = 'Available' if app_data.get('repo') else 'Not Available'
                    
                    # LOC and modules info
                    if app_data.get('loc_k'):
                        cast_record.application_code_complexity_volume = f"{app_data.get('loc_k')}K LOC, {app_data.get('modules')} modules"
                    
                    # Extract quality and security metrics from classification
                    if hasattr(extraction_result, 'get') and extraction_result.get('application_classifications'):
                        for class_record in extraction_result.get('application_classifications', []):
                            if hasattr(class_record, 'to_dict'):
                                class_data = class_record.to_dict()
                            else:
                                class_data = class_record if isinstance(class_record, dict) else {}
                            
                            if class_data.get('app_id') == app_id:
                                cast_record.cloud_suitability = class_data.get('cloud_ready')
                                cast_record.code_design = f"Quality: {class_data.get('quality')}, Security: {class_data.get('security')}"
                                break
                
                db.session.commit()
                logger.info(f"[CASTData] Created/Updated {records_created} records from CAST analysis")
                return records_created
            
            return 0
            
        except Exception as e:
            logger.error(f"[CASTData] Error populating from CAST analysis: {str(e)}", exc_info=True)
            db.session.rollback()
            return 0
    
    @staticmethod
    def bulk_insert_from_dict(cast_data_list):
        """
        Bulk insert or update CASTData records from dictionary list
        
        Args:
            cast_data_list: List of dictionaries with CASTData fields
            
        Returns:
            int: Number of records inserted/updated
        """
        try:
            records_processed = 0
            
            for data_dict in cast_data_list:
                if not data_dict.get('app_id'):
                    logger.warning("[CASTData] Skipping record without app_id")
                    continue
                
                app_id = str(data_dict['app_id']).strip()
                cast_record = CASTData.query.filter_by(app_id=app_id).first()
                
                if not cast_record:
                    cast_record = CASTData(
                        app_id=app_id,
                        app_name=data_dict.get('app_name', '')
                    )
                    db.session.add(cast_record)
                
                # Update all available fields
                for key, value in data_dict.items():
                    if key != 'id' and hasattr(cast_record, key) and value is not None:
                        setattr(cast_record, key, value)
                
                records_processed += 1
            
            db.session.commit()
            logger.info(f"[CASTData] Bulk inserted/updated {records_processed} records")
            return records_processed
            
        except Exception as e:
            logger.error(f"[CASTData] Error bulk inserting records: {str(e)}", exc_info=True)
            db.session.rollback()
            return 0
    
    @staticmethod
    def get_by_app_id(app_id):
        """Retrieve CASTData by app_id"""
        try:
            return CASTData.query.filter_by(app_id=app_id).first()
        except Exception as e:
            logger.error(f"[CASTData] Error retrieving app_id {app_id}: {str(e)}")
            return None
    
    @staticmethod
    def get_all():
        """Retrieve all CASTData records"""
        try:
            return CASTData.query.all()
        except Exception as e:
            logger.error(f"[CASTData] Error retrieving all records: {str(e)}")
            return []

    @staticmethod
    def populate_from_excel_file(file_path):
        """Load CASTData rows from uploaded Excel/CSV file"""
        try:
            file_ext = file_path.lower().split('.')[-1]

            def normalize_columns(dataframe):
                dataframe.columns = [str(col).strip() for col in dataframe.columns]
                return dataframe

            def detect_header_row(raw_dataframe):
                scan_rows = min(len(raw_dataframe), 15)
                for i in range(scan_rows):
                    row_values = [str(v).strip().upper() for v in raw_dataframe.iloc[i].tolist() if pd.notna(v)]
                    if 'APP ID' in row_values and 'APP NAME' in row_values:
                        return i
                return None

            if file_ext == 'csv':
                dataframe = normalize_columns(pd.read_csv(file_path))
                if 'APP ID' not in dataframe.columns:
                    raw_dataframe = pd.read_csv(file_path, header=None)
                    header_idx = detect_header_row(raw_dataframe)
                    if header_idx is not None:
                        header = [str(v).strip() for v in raw_dataframe.iloc[header_idx].tolist()]
                        data_rows = raw_dataframe.iloc[header_idx + 1:].copy()
                        data_rows.columns = header
                        dataframe = normalize_columns(data_rows)
            else:
                dataframe = normalize_columns(pd.read_excel(file_path))
                if 'APP ID' not in dataframe.columns:
                    raw_dataframe = pd.read_excel(file_path, header=None)
                    header_idx = detect_header_row(raw_dataframe)
                    if header_idx is not None:
                        header = [str(v).strip() for v in raw_dataframe.iloc[header_idx].tolist()]
                        data_rows = raw_dataframe.iloc[header_idx + 1:].copy()
                        data_rows.columns = header
                        dataframe = normalize_columns(data_rows)

            column_mapping = {
                'APP ID': 'app_id',
                'APP NAME': 'app_name',
                'REPO NAME': 'repo_name',
                'Repo Name': 'repo_name',
                'REPO': 'repo_name',
                'Repo': 'repo_name',
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
            }

            records_processed = 0

            for _, row in dataframe.iterrows():
                app_id_raw = row.get('APP ID')
                if pd.isna(app_id_raw) or not str(app_id_raw).strip():
                    continue

                app_id = str(app_id_raw).strip()
                cast_record = CASTData.query.filter_by(app_id=app_id).first()

                if not cast_record:
                    cast_record = CASTData(app_id=app_id, app_name='')
                    db.session.add(cast_record)

                for source_col, target_field in column_mapping.items():
                    if source_col in dataframe.columns:
                        value = row.get(source_col)
                        if pd.isna(value):
                            value = None
                        if isinstance(value, str):
                            value = value.strip() if value else None
                        setattr(cast_record, target_field, value)

                records_processed += 1

            db.session.commit()
            logger.info(f"[CASTData] Loaded {records_processed} records from file: {file_path}")
            return records_processed

        except Exception as e:
            logger.error(f"[CASTData] Error loading from Excel/CSV file {file_path}: {str(e)}", exc_info=True)
            db.session.rollback()
            return 0
