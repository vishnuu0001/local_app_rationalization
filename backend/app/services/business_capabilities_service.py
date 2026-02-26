"""Service for importing Business Capabilities from Excel"""
import logging
import pandas as pd
from app import db
from app.models.infrastructure import BusinessCapabilities

logger = logging.getLogger(__name__)


class BusinessCapabilitiesService:
    """Service for managing business capabilities data"""
    
    @staticmethod
    def import_from_excel(excel_path):
        """Import Business Capabilities from Excel file
        
        Expected columns: APP ID, Name, Business owner, Architecture type, Platform Host, Application type, Install type, Capabilities
        """
        try:
            logger.info(f"[BusinessCapabilitiesService] Reading Excel file: {excel_path}")
            
            # Read the Excel file
            df = pd.read_excel(excel_path)
            
            logger.info(f"[BusinessCapabilitiesService] Loaded {len(df)} rows from Excel")
            
            # Track counts
            created_count = 0
            updated_count = 0
            skipped_count = 0
            
            # Import each row
            for idx, row in df.iterrows():
                try:
                    app_id = str(row.get('APP ID', '')).strip()
                    name = str(row.get('Name', '')).strip()
                    
                    # Skip if required fields are missing
                    if not app_id or not name:
                        logger.warning(f"[BusinessCapabilitiesService] Skipping row {idx + 2}: missing APP ID or Name")
                        skipped_count += 1
                        continue
                    
                    # Check if this record already exists
                    existing = BusinessCapabilities.query.filter_by(app_id=app_id).first()
                    
                    if existing:
                        # Update existing record
                        existing.name = name
                        existing.business_owner = str(row.get('Business owner', '')).strip() or None
                        existing.architecture_type = str(row.get('Architecture type', '')).strip() or None
                        existing.platform_host = str(row.get('Platform Host', '')).strip() or None
                        existing.application_type = str(row.get('Application type', '')).strip() or None
                        existing.install_type = str(row.get('Install type', '')).strip() or None
                        existing.capabilities = str(row.get('Capabilities', '')).strip() or None
                        updated_count += 1
                    else:
                        # Create new record
                        capability = BusinessCapabilities(
                            app_id=app_id,
                            name=name,
                            business_owner=str(row.get('Business owner', '')).strip() or None,
                            architecture_type=str(row.get('Architecture type', '')).strip() or None,
                            platform_host=str(row.get('Platform Host', '')).strip() or None,
                            application_type=str(row.get('Application type', '')).strip() or None,
                            install_type=str(row.get('Install type', '')).strip() or None,
                            capabilities=str(row.get('Capabilities', '')).strip() or None
                        )
                        db.session.add(capability)
                        created_count += 1
                    
                    if (created_count + updated_count) % 500 == 0:
                        logger.info(f"[BusinessCapabilitiesService] Processed {created_count + updated_count} records...")
                
                except Exception as row_error:
                    logger.error(f"[BusinessCapabilitiesService] Error processing row {idx + 2}: {str(row_error)}")
                    skipped_count += 1
                    continue
            
            # Commit all changes
            db.session.commit()
            
            logger.info(f"[BusinessCapabilitiesService] Import completed:")
            logger.info(f"  Created: {created_count}")
            logger.info(f"  Updated: {updated_count}")
            logger.info(f"  Skipped: {skipped_count}")
            logger.info(f"  Total: {created_count + updated_count}")
            
            return {
                'success': True,
                'created': created_count,
                'updated': updated_count,
                'skipped': skipped_count,
                'total': created_count + updated_count
            }
        
        except Exception as e:
            logger.error(f"[BusinessCapabilitiesService] Import failed: {str(e)}", exc_info=True)
            db.session.rollback()
            raise
    
    @staticmethod
    def get_all():
        """Get all business capabilities"""
        return BusinessCapabilities.query.all()
    
    @staticmethod
    def get_by_app_id(app_id):
        """Get business capability by APP ID"""
        return BusinessCapabilities.query.filter_by(app_id=app_id).first()
    
    @staticmethod
    def search(query):
        """Search business capabilities by name or capabilities"""
        return BusinessCapabilities.query.filter(
            db.or_(
                BusinessCapabilities.name.ilike(f"%{query}%"),
                BusinessCapabilities.capabilities.ilike(f"%{query}%"),
                BusinessCapabilities.app_id.ilike(f"%{query}%")
            )
        ).all()
