"""Service for handling Industry Templates data extraction and storage"""

import logging
import pandas as pd
from datetime import datetime
from app import db
from app.models.industry_data import IndustryTemplate, IndustryData

logger = logging.getLogger(__name__)


class IndustryDataService:
    """Service to extract Industry Templates data and store in IndustryData table"""
    
    # Expected column names in the Industry_Templates.xlsx file
    EXPECTED_COLUMNS = {
        'APP ID': 'app_id',
        'APP Name': 'app_name',
        'Business owner': 'business_owner',
        'Architecture type': 'architecture_type',
        'Platform Host': 'platform_host',
        'Application type': 'application_type',
        'Install type': 'install_type',
        'Capabilities': 'capabilities',
    }
    
    @staticmethod
    def extract_from_excel(file_path, filename):
        """
        Extract Industry Templates data from Excel file
        
        Args:
            file_path: Full path to the Excel file
            filename: Original filename for metadata
            
        Returns:
            tuple: (file_id, IndustryTemplate object, records_count)
        """
        try:
            # Read the Excel file
            df = pd.read_excel(file_path)
            
            logger.info(f"[IndustryData] Loaded Excel file: {filename} with {len(df)} rows")
            logger.info(f"[IndustryData] Columns found: {list(df.columns)}")
            
            # Validate that required columns exist (case-insensitive)
            df_columns_lower = {col.lower().strip(): col for col in df.columns}
            required_cols_lower = {k.lower().strip(): v for k, v in IndustryDataService.EXPECTED_COLUMNS.items()}
            
            logger.info(f"[IndustryData] Required columns (lowercase): {list(required_cols_lower.keys())}")
            logger.info(f"[IndustryData] DataFrame columns (lowercase): {list(df_columns_lower.keys())}")
            
            # Map Excel columns to our field names
            column_mapping = {}
            for expected_col_lower, field_name in required_cols_lower.items():
                if expected_col_lower in df_columns_lower:
                    actual_col_name = df_columns_lower[expected_col_lower]
                    column_mapping[actual_col_name] = field_name
                    logger.info(f"[IndustryData] Mapped '{actual_col_name}' -> '{field_name}'")
                else:
                    logger.warning(f"[IndustryData] Expected column '{expected_col_lower}' not found in Excel file")
            
            if not column_mapping:
                raise ValueError(f"No matching columns found in Excel file. Expected columns: {', '.join(IndustryDataService.EXPECTED_COLUMNS.keys())}. Found: {', '.join(df.columns)}")
            
            logger.info(f"[IndustryData] Column mapping: {column_mapping}")
            
            # Create IndustryTemplate metadata record
            import uuid
            file_id = str(uuid.uuid4())
            
            # Check for duplicate file
            existing_template = IndustryTemplate.query.filter_by(filename=filename).first()
            if existing_template:
                # Delete old records associated with this file
                IndustryData.query.filter_by(template_id=existing_template.id).delete()
                db.session.delete(existing_template)
                db.session.commit()
                logger.info(f"[IndustryData] Deleted existing template for: {filename}")
            
            # Create new template
            template = IndustryTemplate(
                file_id=file_id,
                filename=filename,
                file_path=file_path
            )
            db.session.add(template)
            db.session.flush()  # Flush to get the template ID
            template_id = template.id
            
            # Process and insert data rows
            records_created = 0
            errors = []
            
            for idx, row in df.iterrows():
                try:
                    # Map row data using column_mapping
                    data = {}
                    for excel_col, field_name in column_mapping.items():
                        if excel_col in row.index:
                            value = row[excel_col]
                            # Convert NaN values to None
                            if pd.isna(value):
                                data[field_name] = None
                            else:
                                # Convert to string and strip whitespace
                                data[field_name] = str(value).strip() if not isinstance(value, (int, float)) else value
                        else:
                            logger.warning(f"[IndustryData] Column '{excel_col}' not found in row {idx + 2}")
                            data[field_name] = None
                    
                    logger.debug(f"[IndustryData] Row {idx + 2} data: {data}")
                    
                    # Validate required fields
                    app_id = data.get('app_id')
                    app_name = data.get('app_name')
                    
                    if not app_id or (isinstance(app_id, str) and not app_id.strip()):
                        logger.warning(f"[IndustryData] Row {idx + 2} skipped: Missing or empty APP ID. Value: '{app_id}'")
                        continue
                    
                    if not app_name or (isinstance(app_name, str) and not app_name.strip()):
                        logger.warning(f"[IndustryData] Row {idx + 2} skipped: Missing or empty APP Name. Value: '{app_name}'")
                        continue
                    
                    # Check if record already exists (update or create)
                    industry_record = IndustryData.query.filter_by(app_id=app_id).first()
                    
                    if industry_record:
                        # Update existing record
                        for key, value in data.items():
                            setattr(industry_record, key, value)
                        industry_record.template_id = template_id
                        logger.info(f"[IndustryData] Updated record for APP ID: {app_id}")
                    else:
                        # Create new record
                        industry_record = IndustryData(
                            template_id=template_id,
                            **data
                        )
                        db.session.add(industry_record)
                        logger.info(f"[IndustryData] Created new record for APP ID: {app_id}")
                    
                    records_created += 1
                
                except Exception as e:
                    error_msg = f"Row {idx + 2}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"[IndustryData] Error processing row {idx + 2}: {str(e)}", exc_info=True)
                    continue
            
            # Update template record count and processed timestamp
            template.record_count = records_created
            template.processed_at = datetime.utcnow()
            
            # Commit all changes
            db.session.commit()
            
            logger.info(f"[IndustryData] Successfully processed {records_created} records from {filename}")
            if errors:
                logger.warning(f"[IndustryData] Encountered {len(errors)} errors during processing: {errors}")
            
            return file_id, template, records_created, errors
        
        except Exception as e:
            logger.error(f"[IndustryData] Error extracting from Excel: {str(e)}", exc_info=True)
            db.session.rollback()
            raise
    
    @staticmethod
    def get_all_industry_data(template_id=None):
        """
        Get all Industry Data records, optionally filtered by template
        
        Args:
            template_id: Optional template ID to filter
            
        Returns:
            list: List of IndustryData dictionaries
        """
        try:
            if template_id:
                records = IndustryData.query.filter_by(template_id=template_id).all()
            else:
                records = IndustryData.query.all()
            
            return [record.to_dict() for record in records]
        except Exception as e:
            logger.error(f"[IndustryData] Error retrieving industry data: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def get_templates_with_count():
        """
        Get all templates with their record counts
        
        Returns:
            list: List of template dictionaries with record counts
        """
        try:
            templates = IndustryTemplate.query.all()
            results = []
            for template in templates:
                data = template.to_dict()
                data['record_count'] = IndustryData.query.filter_by(template_id=template.id).count()
                results.append(data)
            return results
        except Exception as e:
            logger.error(f"[IndustryData] Error retrieving templates: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def delete_template(template_id):
        """
        Delete a template and all associated industry data
        
        Args:
            template_id: Template ID to delete
            
        Returns:
            int: Number of records deleted
        """
        try:
            # Delete associated industry data
            records_deleted = IndustryData.query.filter_by(template_id=template_id).delete()
            
            # Delete template
            template = IndustryTemplate.query.filter_by(id=template_id).first()
            if template:
                db.session.delete(template)
                db.session.commit()
                logger.info(f"[IndustryData] Deleted template {template_id} and {records_deleted} associated records")
            
            return records_deleted
        except Exception as e:
            logger.error(f"[IndustryData] Error deleting template: {str(e)}", exc_info=True)
            db.session.rollback()
            return 0
