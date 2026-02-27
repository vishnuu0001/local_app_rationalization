"""Service for extracting Corent data and populating CorentData table"""

import logging
import pandas as pd
from app import db
from app.models.corent_data import CorentData

logger = logging.getLogger(__name__)

class CorentDataService:
    """Service to extract Corent infrastructure data and store in CorentData table"""
    
    @staticmethod
    def populate_from_infrastructure(infrastructure):
        """
        Extract and populate CorentData from Infrastructure model
        
        Args:
            infrastructure: Infrastructure object from extraction
            
        Returns:
            list: CorentData records created/updated
        """
        try:
            if not infrastructure:
                logger.warning("[CorentData] No infrastructure data provided")
                return 0
            
            records_created = 0
            
            # Extract from infrastructure servers data
            servers = []
            try:
                if hasattr(infrastructure, 'servers'):
                    servers = infrastructure.servers if infrastructure.servers else []
            except Exception as e:
                logger.warning(f"[CorentData] Could not access servers: {str(e)}")
                servers = []
            
            if servers:
                for server in servers:
                    try:
                        # Create or update CorentData record
                        app_id = getattr(server, 'server_name', 'UNKNOWN').upper().strip() if hasattr(server, 'server_name') else 'UNKNOWN'
                        
                        if not app_id or app_id == 'UNKNOWN':
                            logger.warning("[CorentData] Skipping server without name")
                            continue
                        
                        corent_record = CorentData.query.filter_by(app_id=app_id).first()
                        
                        if not corent_record:
                            corent_record = CorentData(app_id=app_id)
                            db.session.add(corent_record)
                            records_created += 1
                        
                        # Safely populate fields from server data
                        corent_record.app_name = getattr(server, 'server_name', '')
                        corent_record.server_type = getattr(server, 'server_type', '')
                        corent_record.operating_system = getattr(server, 'environment', '')
                        corent_record.platform_host = getattr(server, 'deployment_footprint', '')
                        
                        # Extract tech stack if available
                        installed_techs = getattr(server, 'installed_techs', None)
                        if installed_techs:
                            corent_record.cpu_requirement = str(installed_techs)[:255]
                    
                    except Exception as e:
                        logger.error(f"[CorentData] Error processing server: {str(e)}", exc_info=True)
                        continue
                
                db.session.commit()
                logger.info(f"[CorentData] Created/Updated {records_created} records from Infrastructure data")
                return records_created
            else:
                logger.info("[CorentData] No servers found in infrastructure data")
                return 0
            
        except Exception as e:
            logger.error(f"[CorentData] Error populating from infrastructure: {str(e)}", exc_info=True)
            db.session.rollback()
            return 0
    
    @staticmethod
    def bulk_insert_from_dict(corent_data_list):
        """
        Bulk insert or update CorentData records from dictionary list
        
        Args:
            corent_data_list: List of dictionaries with CorentData fields
            
        Returns:
            int: Number of records inserted/updated
        """
        try:
            records_processed = 0
            
            for data_dict in corent_data_list:
                if not data_dict.get('app_id'):
                    logger.warning("[CorentData] Skipping record without app_id")
                    continue
                
                app_id = str(data_dict['app_id']).strip()
                corent_record = CorentData.query.filter_by(app_id=app_id).first()
                
                if not corent_record:
                    corent_record = CorentData(app_id=app_id)
                    db.session.add(corent_record)
                
                # Update all available fields
                for key, value in data_dict.items():
                    if key != 'id' and hasattr(corent_record, key) and value is not None:
                        setattr(corent_record, key, value)
                
                records_processed += 1
            
            db.session.commit()
            logger.info(f"[CorentData] Bulk inserted/updated {records_processed} records")
            return records_processed
            
        except Exception as e:
            logger.error(f"[CorentData] Error bulk inserting records: {str(e)}", exc_info=True)
            db.session.rollback()
            return 0
    
    @staticmethod
    def get_by_app_id(app_id):
        """Retrieve CorentData by app_id"""
        try:
            return CorentData.query.filter_by(app_id=app_id).first()
        except Exception as e:
            logger.error(f"[CorentData] Error retrieving app_id {app_id}: {str(e)}")
            return None
    
    @staticmethod
    def get_all():
        """Retrieve all CorentData records"""
        try:
            return CorentData.query.all()
        except Exception as e:
            logger.error(f"[CorentData] Error retrieving all records: {str(e)}")
            return []

    @staticmethod
    def populate_from_excel_file(file_path):
        """Load CorentData rows from uploaded Excel/CSV infrastructure file"""
        try:
            file_ext = file_path.lower().split('.')[-1]

            if file_ext == 'csv':
                dataframe = pd.read_csv(file_path)
            else:
                dataframe = pd.read_excel(file_path)

            dataframe.columns = [str(col).strip() for col in dataframe.columns]

            column_mapping = {
                'APP ID': 'app_id',
                'APP Name': 'app_name',
                'ArchitectureType': 'architecture_type',
                'BusinessOwner': 'business_owner',
                'PlatformHost': 'platform_host',
                'Server Type': 'server_type',
                'Operating System': 'operating_system',
                'Environment': 'environment',
                'INSTALL TYPE': 'install_type',
                'Cloud Suitability': 'cloud_suitability',
                'Volume of External Dependencies': 'volume_external_dependencies',
                'Deployment Geography': 'deployment_geography',
            }

            records_processed = 0

            for _, row in dataframe.iterrows():
                app_id_raw = row.get('APP ID')
                if pd.isna(app_id_raw) or not str(app_id_raw).strip():
                    continue

                app_id = str(app_id_raw).strip()
                corent_record = CorentData.query.filter_by(app_id=app_id).first()

                if not corent_record:
                    corent_record = CorentData(app_id=app_id)
                    db.session.add(corent_record)

                for source_col, target_field in column_mapping.items():
                    if source_col in dataframe.columns:
                        value = row.get(source_col)
                        if pd.isna(value):
                            value = None
                        if isinstance(value, str):
                            value = value.strip() if value else None
                        setattr(corent_record, target_field, value)

                if not corent_record.app_name:
                    corent_record.app_name = app_id

                records_processed += 1

            db.session.commit()
            logger.info(f"[CorentData] Loaded {records_processed} records from file: {file_path}")
            return records_processed

        except Exception as e:
            logger.error(f"[CorentData] Error loading from Excel/CSV file {file_path}: {str(e)}", exc_info=True)
            db.session.rollback()
            return 0
