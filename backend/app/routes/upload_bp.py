from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
import os
import logging
import uuid
import pandas as pd
from datetime import datetime
from app import db
from app.services.infrastructure_service import InfrastructureService
from app.services.cast_service import CASTService
from app.services.cast_analysis_service import CASTAnalysisService
from app.services.pdf_extraction_service import PDFExtractionService
from app.services.business_capabilities_service import BusinessCapabilitiesService
from app.services.corent_data_service import CorentDataService
from app.services.cast_data_service import CASTDataService
from app.services.industry_data_service import IndustryDataService
from app.models.infrastructure import Infrastructure, InfrastructureDiscovery, BusinessCapabilities
from app.models.code import CodeRepository
from app.models.application import Application
from app.models.pdf_report import PDFReport
from app.models.cast import CASTAnalysis, ApplicationInventory, ApplicationClassification, InternalArchitecture, HighRiskApplication
from app.models.industry_data import IndustryTemplate, IndustryData

logger = logging.getLogger(__name__)

bp = Blueprint('upload', __name__, url_prefix='/api/upload')

ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'csv'}


def get_upload_folder():
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp/uploads')
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder


def resolve_file_path(file_path):
    if os.path.isabs(file_path):
        return file_path

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.normpath(os.path.join(project_root, file_path))


def get_file_record_by_id(file_id):
    infra = Infrastructure.query.filter_by(file_id=file_id).first()
    if infra and infra.file_path:
        return infra.file_path, infra.filename

    code = CodeRepository.query.filter_by(file_id=file_id).first()
    if code and code.file_path:
        return code.file_path, code.filename

    return None, None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/infrastructure', methods=['POST'])
def upload_infrastructure():
    """Upload infrastructure discovery file (Corent output)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        filename = secure_filename(file.filename)
        upload_folder = get_upload_folder()
        filepath = os.path.join(upload_folder, filename)
        
        # Check for duplicate file (same filename)
        existing_infra = Infrastructure.query.filter_by(filename=filename).first()
        
        if existing_infra:
            # Delete old extracted PDFReports associated with this file
            deleted_reports = PDFReport.query.filter_by(source_pdf=existing_infra.file_path).delete()
            db.session.commit()
            print(f"[Upload] Duplicate file detected: {filename}. Updating existing record. Deleted {deleted_reports} PDFReport entries.")
        
        file.save(filepath)
        
        # Determine file type and extract accordingly
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext == 'pdf':
            # Extract infrastructure data from PDF
            file_id, infra = InfrastructureService.extract_from_pdf(filepath, filename)
            
            # Populate CorentData table from extracted infrastructure
            try:
                CorentDataService.populate_from_infrastructure(infra)
                logger.info(f"[Upload] CorentData populated for file: {filename}")
            except Exception as e:
                logger.error(f"[Upload] Error populating CorentData: {str(e)}", exc_info=True)
            
            return jsonify({
                'success': True,
                'file_id': file_id,
                'filename': filename,
                'is_update': existing_infra is not None,
                'infrastructure': infra.to_dict()
            }), 201
        elif file_ext in ['xlsx', 'xls', 'csv']:
            # For Excel/CSV files, store without extraction (data preview available through file endpoint)
            file_id = str(uuid.uuid4())
            upload_record = Infrastructure(
                file_id=file_id,
                filename=filename,
                file_path=filepath
            )
            db.session.add(upload_record)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'file_id': file_id,
                'filename': filename,
                'is_update': existing_infra is not None,
                'infrastructure': None,
                'message': 'Excel/CSV file stored successfully. Use preview to view contents.'
            }), 201
        else:
            return jsonify({'error': f'Unsupported file type: {file_ext}'}), 400
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error uploading infrastructure file: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.route('/code-analysis', methods=['POST'])
def upload_code_analysis():
    """Upload code analysis file (CAST output)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        filename = secure_filename(file.filename)
        upload_folder = get_upload_folder()
        filepath = os.path.join(upload_folder, filename)
        
        # Check for duplicate file (same filename)
        existing_code = CodeRepository.query.filter_by(filename=filename).first()
        
        if existing_code:
            # Delete old extracted PDFReports associated with this file
            deleted_reports = PDFReport.query.filter_by(source_pdf=existing_code.file_path).delete()
            db.session.commit()
            logger.info(f"[Upload] Duplicate file detected: {filename}. Updating existing record. Deleted {deleted_reports} PDFReport entries.")
        
        file.save(filepath)
        logger.info(f"[Upload] File saved to {filepath}")
        
        # Determine file type and extract accordingly
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext == 'pdf':
            # Extract code data from PDF
            file_id, repo = CASTService.extract_from_pdf(filepath, filename)
            return jsonify({
                'success': True,
                'file_id': file_id,
                'filename': filename,
                'is_update': existing_code is not None,
                'repository': repo.to_dict()
            }), 201
        elif file_ext in ['xlsx', 'xls', 'csv']:
            # For Excel/CSV files, store without extraction (data preview available through file endpoint)
            file_id = str(uuid.uuid4())
            code_record = CodeRepository(
                file_id=file_id,
                filename=filename,
                file_path=filepath,
                repo_url='',
                repo_name=filename.replace('.xlsx', '').replace('.xls', '').replace('.csv', '')
            )
            db.session.add(code_record)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'file_id': file_id,
                'filename': filename,
                'is_update': existing_code is not None,
                'repository': None,
                'message': 'Excel/CSV file stored successfully. Use extract to process the file.'
            }), 201
        else:
            return jsonify({'error': f'Unsupported file type: {file_ext}'}), 400
    
    except Exception as e:
        logger.error(f"[Upload] Error uploading code analysis: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Code analysis upload failed: {str(e)}'}), 500

@bp.route('/files', methods=['GET'])
def get_uploaded_files():
    """Get list of uploaded files"""
    infra_files = Infrastructure.query.all()
    code_files = CodeRepository.query.all()
    
    files = []
    
    for inf in infra_files:
        files.append({
            'id': inf.id,
            'file_id': inf.file_id,
            'filename': inf.filename,
            'file_path': inf.file_path,
            'type': 'Infrastructure',
            'uploaded_at': inf.uploaded_at.isoformat(),
            'size_kb': 1024,  # Placeholder
            'status': 'Ready'
        })
    
    for code in code_files:
        files.append({
            'id': code.id,
            'file_id': code.file_id,
            'filename': code.filename,
            'file_path': code.file_path,
            'type': 'Code Analysis',
            'uploaded_at': code.uploaded_at.isoformat(),
            'size_kb': 2048,  # Placeholder
            'status': 'Ready'
        })
    
    return jsonify({
        'files': files,
        'total': len(files)
    }), 200

@bp.route('/pdf/<file_id>', methods=['GET'])
def get_pdf_file(file_id):
    """Serve file by file_id (PDF or Excel)"""
    try:
        file_path, _ = get_file_record_by_id(file_id)
        
        if not file_path:
            return jsonify({'error': f'File not found in database for file_id: {file_id}'}), 404

        file_path = resolve_file_path(file_path)
        
        print(f"[FILE] Absolute path: {file_path}")
        print(f"[FILE] File exists: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            return jsonify({'error': f'File not found on disk: {file_path}'}), 404
        
        # Detect file type and set appropriate MIME type
        file_ext = os.path.splitext(file_path)[1].lower()
        mime_type = 'application/pdf'
        
        if file_ext in ['.xlsx', '.xls', '.xlsm']:
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif file_ext == '.csv':
            mime_type = 'text/csv'
        
        print(f"[FILE] MIME type: {mime_type}")
        
        # Serve the file with inline display
        response = send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=False,
            download_name=os.path.basename(file_path)
        )
        
        # Force inline display for PDFs (prevents downloading)
        if file_ext == '.pdf':
            response.headers['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        
        return response
        
    except Exception as e:
        print(f"[FILE] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error serving file: {str(e)}'}), 500


@bp.route('/preview/<file_id>', methods=['GET'])
def preview_uploaded_file(file_id):
    """Preview uploaded Excel/CSV file as JSON to avoid browser binary-fetch issues"""
    try:
        max_rows = request.args.get('max_rows', 500, type=int)
        file_path, filename = get_file_record_by_id(file_id)

        if not file_path:
            return jsonify({'error': f'File not found in database for file_id: {file_id}'}), 404

        file_path = resolve_file_path(file_path)
        if not os.path.exists(file_path):
            return jsonify({'error': f'File not found on disk: {file_path}'}), 404

        file_ext = os.path.splitext(file_path)[1].lower()

        def to_preview_records(dataframe):
            dataframe = dataframe.where(pd.notnull(dataframe), None)
            return dataframe.head(max_rows).to_dict(orient='records')

        def fallback_sheet_preview(sheet_name):
            raw_dataframe = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            raw_dataframe = raw_dataframe.dropna(how='all')

            if raw_dataframe.empty:
                return []

            # Choose the most likely header row from first 10 rows by max non-empty cells
            scan_rows = min(len(raw_dataframe), 10)
            header_index = 0
            max_non_empty = -1
            for i in range(scan_rows):
                row = raw_dataframe.iloc[i]
                non_empty = int(row.notna().sum())
                if non_empty > max_non_empty:
                    max_non_empty = non_empty
                    header_index = i

            header_values = raw_dataframe.iloc[header_index].tolist()
            normalized_headers = []
            for idx, header in enumerate(header_values):
                header_text = str(header).strip() if header is not None and str(header).strip() else f'Column {idx + 1}'
                normalized_headers.append(header_text)

            data_rows = raw_dataframe.iloc[header_index + 1:header_index + 1 + max_rows].copy()
            data_rows = data_rows.dropna(how='all')
            if data_rows.empty:
                return []

            data_rows.columns = normalized_headers
            data_rows = data_rows.where(pd.notnull(data_rows), None)
            return data_rows.to_dict(orient='records')

        if file_ext == '.csv':
            dataframe = pd.read_csv(file_path)
            preview_rows = to_preview_records(dataframe)

            return jsonify({
                'success': True,
                'file_id': file_id,
                'filename': filename,
                'file_type': 'csv',
                'sheet_names': ['Sheet1'],
                'sheets': {
                    'Sheet1': preview_rows
                },
                'max_rows': max_rows,
            }), 200

        if file_ext in ['.xlsx', '.xls', '.xlsm']:
            workbook = pd.read_excel(file_path, sheet_name=None)
            sheets = {}
            sheet_names = []

            for sheet_name, dataframe in workbook.items():
                safe_name = str(sheet_name)
                sheet_names.append(safe_name)
                preview_rows = to_preview_records(dataframe)

                # Some CAST Excel sheets have title/blank rows that cause default header parsing
                # to return empty data. Fallback to header=None parsing in that case.
                if not preview_rows:
                    preview_rows = fallback_sheet_preview(sheet_name)

                sheets[safe_name] = preview_rows

            return jsonify({
                'success': True,
                'file_id': file_id,
                'filename': filename,
                'file_type': 'excel',
                'sheet_names': sheet_names,
                'sheets': sheets,
                'max_rows': max_rows,
            }), 200

        return jsonify({'error': f'Preview not supported for file type: {file_ext}'}), 400

    except Exception as e:
        logger.error(f"[Preview] Error previewing file {file_id}: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to preview file: {str(e)}'}), 500

@bp.route('/file/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Delete uploaded file and associated extracted data"""
    pdf_reports_deleted = 0
    
    infra = Infrastructure.query.filter_by(file_id=file_id).first()
    if infra:
        # Delete associated PDFReport records (cascading deletion of extracted data)
        if infra.file_path:
            pdf_reports_deleted = PDFReport.query.filter_by(source_pdf=infra.file_path).delete()
            db.session.commit()
            print(f"[Delete] Deleted {pdf_reports_deleted} PDFReport entries for {infra.file_path}")
        
        # Delete file from disk if it exists
        if infra.file_path and os.path.exists(infra.file_path):
            try:
                os.remove(infra.file_path)
                print(f"[Delete] Removed file from disk: {infra.file_path}")
            except Exception as e:
                print(f"Warning: Could not delete file {infra.file_path}: {str(e)}")
        
        db.session.delete(infra)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Infrastructure file deleted',
            'pdf_reports_deleted': pdf_reports_deleted
        }), 200
    
    code = CodeRepository.query.filter_by(file_id=file_id).first()
    if code:
        # Delete associated PDFReport records (cascading deletion of extracted data)
        if code.file_path:
            pdf_reports_deleted = PDFReport.query.filter_by(source_pdf=code.file_path).delete()
            db.session.commit()
            print(f"[Delete] Deleted {pdf_reports_deleted} PDFReport entries for {code.file_path}")
        
        # Delete file from disk if it exists
        if code.file_path and os.path.exists(code.file_path):
            try:
                os.remove(code.file_path)
                print(f"[Delete] Removed file from disk: {code.file_path}")
            except Exception as e:
                print(f"Warning: Could not delete file {code.file_path}: {str(e)}")
        
        db.session.delete(code)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Code analysis file deleted',
            'pdf_reports_deleted': pdf_reports_deleted
        }), 200
    
    return jsonify({'error': 'File not found'}), 404


@bp.route('/extract-pdf/<file_id>', methods=['POST'])
def extract_pdf_data(file_id):
    """Extract structured data from a PDF and store in database with pagination support"""
    try:
        # Parse pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Find the file
        infra = Infrastructure.query.filter_by(file_id=file_id).first()
        if infra:
            file_path = infra.file_path
            report_type = 'infrastructure'
        else:
            code = CodeRepository.query.filter_by(file_id=file_id).first()
            if not code:
                return jsonify({'error': 'File not found'}), 404
            
            file_path = code.file_path
            report_type = 'code_analysis'
        
        # Convert relative path to absolute if needed
        if not os.path.isabs(file_path):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            file_path = os.path.normpath(os.path.join(project_root, file_path))
        
        logger.info(f"[PDF Extract] Processing {report_type}: {file_path}")
        
        if report_type == 'infrastructure':
            # Extract Infrastructure & Network Discovery table
            rows = InfrastructureService.extract_pdf_table(file_path)
            
            if not rows:
                logger.warning("[PDF Extract] No rows extracted from PDF")
                return jsonify({
                    'error': 'No data found in PDF. The PDF may not contain a valid Infrastructure & Network Discovery table.',
                    'extracted_rows': 0
                }), 400
            
            # Store extracted rows in database using BATCH operations
            # This is much faster than individual queries per row
            logger.info(f"[PDF Extract] Storing {len(rows)} rows to database (batch mode)")
            
            new_apps = []
            updated_count = 0
            
            for row_data in rows:
                app_id = row_data.get('app_id', '')
                
                # Check if this application already exists
                existing = InfrastructureDiscovery.query.filter_by(app_id=app_id).first()
                
                if existing:
                    # Update existing record
                    existing.name = row_data.get('name', '')
                    existing.business_owner = row_data.get('business_owner')
                    existing.architecture_type = row_data.get('architecture_type')
                    existing.platform_host = row_data.get('platform_host')
                    existing.application_type = row_data.get('application_type')
                    existing.install_type = row_data.get('install_type')
                    existing.capabilities = row_data.get('capabilities')
                    updated_count += 1
                else:
                    # Create new record
                    app = InfrastructureDiscovery(
                        infrastructure_id=infra.id,
                        app_id=app_id,
                        name=row_data.get('name', ''),
                        business_owner=row_data.get('business_owner'),
                        architecture_type=row_data.get('architecture_type'),
                        platform_host=row_data.get('platform_host'),
                        application_type=row_data.get('application_type'),
                        install_type=row_data.get('install_type'),
                        capabilities=row_data.get('capabilities')
                    )
                    new_apps.append(app)
            
            # Bulk insert all new records at once
            if new_apps:
                db.session.bulk_save_objects(new_apps, return_defaults=False)
            
            # Commit all changes at once
            try:
                db.session.commit()
                extracted_count = len(rows)
                logger.info(f"[PDF Extract] Database commit complete: {extracted_count} total rows ({updated_count} updated, {len(new_apps)} inserted)")
            except Exception as commit_error:
                db.session.rollback()
                logger.error(f"[PDF Extract] Database commit failed: {str(commit_error)}")
                extracted_count = 0
            
            # Get paginated results
            paginated_apps = InfrastructureDiscovery.query.filter_by(
                infrastructure_id=infra.id
            ).paginate(page=page, per_page=per_page, error_out=False)
            
            apps_data = [app.to_dict() for app in paginated_apps.items]
            
            return jsonify({
                'success': True,
                'message': f'Infrastructure & Network Discovery table extraction completed',
                'extracted_rows': {
                    'main_table': extracted_count,
                    'exceptions_table': 0,
                    'total': extracted_count
                },
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': paginated_apps.total,
                    'pages': paginated_apps.pages,
                    'has_next': paginated_apps.has_next,
                    'has_prev': paginated_apps.has_prev
                },
                'data': apps_data
            }), 201
        else:
            # Extract and store code analysis
            pdf_report = PDFExtractionService.extract_and_store(file_path, report_type)
            
            return jsonify({
                'success': True,
                'message': 'PDF extraction completed',
                'report_id': pdf_report.id,
                'extracted_rows': {
                    'main_table': pdf_report.payload['sections']['application_discovery_summary']['row_count'],
                    'exceptions_table': pdf_report.payload['sections']['exceptions_gaps_discovery_notes']['row_count']
                }
            }), 201
        
    except ImportError as e:
        logger.error(f"[PDF Extract] Import error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Missing dependency: {str(e)}. Install PyMuPDF: pip install PyMuPDF'}), 500
    except FileNotFoundError as e:
        logger.error(f"[PDF Extract] File not found: {str(e)}", exc_info=True)
        return jsonify({'error': f'File not found: {str(e)}'}), 404
    except Exception as e:
        logger.error(f"[PDF Extract] Error: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Extraction failed: {str(e)}'}), 500


@bp.route('/extract-cast-analysis/<file_id>', methods=['POST'])
def extract_cast_analysis_data(file_id):
    """Extract CAST Analysis data from PDF or Excel and store in tables"""
    try:
        # Find the CAST file
        cast_file = CodeRepository.query.filter_by(file_id=file_id).first()
        if not cast_file:
            return jsonify({'error': 'File not found'}), 404
        
        file_path = cast_file.file_path
        
        # Convert relative path to absolute if needed
        if not os.path.isabs(file_path):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            file_path = os.path.normpath(os.path.join(project_root, file_path))
        
        logger.info(f"[CAST Extract] Processing file: {file_path}")
        
        # Detect file type
        file_ext = os.path.splitext(file_path)[1].lower()
        filename = cast_file.filename
        
        # Handle Excel/CSV files - just store metadata, no extraction
        if file_ext in ['.xlsx', '.xls', '.csv', '.xlsm']:
            logger.info(f"[CAST Extract] Excel/CSV file detected: {filename}. Loading CASTData rows.")
            
            # Create or update CAST Analysis parent record
            cast_analysis = CASTAnalysis.query.filter_by(file_id=file_id).first()
            if not cast_analysis:
                cast_analysis = CASTAnalysis(
                    file_id=file_id,
                    filename=filename,
                    file_path=file_path
                )
                db.session.add(cast_analysis)
                db.session.commit()
            
            # Populate CASTData from uploaded Excel/CSV
            cast_records = CASTDataService.populate_from_excel_file(file_path)

            # Mark as extracted
            cast_analysis.extracted_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Excel/CSV file processed successfully. CAST data loaded.',
                'file_type': 'excel',
                'sections': {
                    'application_inventory': {
                        'label': 'Application Inventory',
                        'count': cast_records,
                        'data': [],
                        'total': cast_records
                    },
                    'application_classification': {
                        'label': 'Application Classification',
                        'count': 0,
                        'data': [],
                        'total': 0
                    },
                    'internal_architecture': {
                        'label': 'Internal Architecture',
                        'count': 0,
                        'data': [],
                        'total': 0
                    },
                    'high_risk_applications': {
                        'label': 'High-Risk Applications',
                        'count': 0,
                        'data': [],
                        'total': 0
                    }
                },
                'extracted_rows': {
                    'app_inventory': cast_records,
                    'app_classification': 0,
                    'internal_architecture': 0,
                    'high_risk_applications': 0,
                    'total': cast_records
                }
            }), 201
        
        # Create or get CAST Analysis parent record
        cast_analysis = CASTAnalysis.query.filter_by(file_id=file_id).first()
        if not cast_analysis:
            cast_analysis = CASTAnalysis(
                file_id=file_id,
                filename=filename,
                file_path=file_path
            )
            db.session.add(cast_analysis)
            db.session.commit()
        
        # Extract all tables from PDF
        extraction_result = CASTAnalysisService.extract_pdf_tables(file_path)
        
        # Store Application Inventory
        inventory_rows = extraction_result['app_inventory']
        if inventory_rows:
            logger.info(f"[CAST Extract] Storing {len(inventory_rows)} Application Inventory rows")
            
            new_inventories = []
            for row_data in inventory_rows:
                existing = ApplicationInventory.query.filter_by(
                    cast_analysis_id=cast_analysis.id,
                    app_id=row_data['app_id']
                ).first()
                
                if existing:
                    # Update existing
                    for key, value in row_data.items():
                        setattr(existing, key, value)
                else:
                    # Create new
                    inventory = ApplicationInventory(
                        cast_analysis_id=cast_analysis.id,
                        **row_data
                    )
                    new_inventories.append(inventory)
            
            if new_inventories:
                db.session.bulk_save_objects(new_inventories, return_defaults=False)
            db.session.commit()
        
        # Store Application Classification
        classification_rows = extraction_result['app_classification']
        if classification_rows:
            logger.info(f"[CAST Extract] Storing {len(classification_rows)} Application Classification rows")
            
            new_classifications = []
            for row_data in classification_rows:
                existing = ApplicationClassification.query.filter_by(
                    cast_analysis_id=cast_analysis.id,
                    app_id=row_data['app_id']
                ).first()
                
                if existing:
                    # Update existing
                    for key, value in row_data.items():
                        setattr(existing, key, value)
                else:
                    # Create new
                    classification = ApplicationClassification(
                        cast_analysis_id=cast_analysis.id,
                        **row_data
                    )
                    new_classifications.append(classification)
            
            if new_classifications:
                db.session.bulk_save_objects(new_classifications, return_defaults=False)
            db.session.commit()
        
        # Store Internal Architecture
        architecture_rows = extraction_result['internal_architecture']
        if architecture_rows:
            logger.info(f"[CAST Extract] Storing {len(architecture_rows)} Internal Architecture rows")
            
            new_architectures = []
            for row_data in architecture_rows:
                # Note: Internal Architecture doesn't have UNIQUE constraint, so we always create new
                architecture = InternalArchitecture(
                    cast_analysis_id=cast_analysis.id,
                    **row_data
                )
                new_architectures.append(architecture)
            
            if new_architectures:
                db.session.bulk_save_objects(new_architectures, return_defaults=False)
            db.session.commit()
        
        # Store High-Risk Applications
        high_risk_rows = extraction_result.get('high_risk_applications', [])
        if high_risk_rows:
            logger.info(f"[CAST Extract] Storing {len(high_risk_rows)} High-Risk Applications rows")
            
            new_high_risk = []
            for row_data in high_risk_rows:
                # Note: High-Risk Applications doesn't have UNIQUE constraint, so we always create new
                high_risk = HighRiskApplication(
                    cast_analysis_id=cast_analysis.id,
                    **row_data
                )
                new_high_risk.append(high_risk)
            
            if new_high_risk:
                db.session.bulk_save_objects(new_high_risk, return_defaults=False)
            db.session.commit()
        
        # Update extraction time
        cast_analysis.extracted_at = datetime.utcnow()
        db.session.commit()
        
        # Populate CASTData table from extracted inventory
        try:
            CASTDataService.populate_from_cast_analysis(extraction_result)
            logger.info(f"[CAST Extract] CASTData populated for file: {filename}")
        except Exception as e:
            logger.error(f"[CAST Extract] Error populating CASTData: {str(e)}", exc_info=True)
        
        logger.info(f"[CAST Extract] Extraction complete")
        
        # Return results in sections
        return jsonify({
            'success': True,
            'message': 'CAST Analysis extraction completed',
            'sections': {
                'application_inventory': {
                    'label': 'Application Inventory',
                    'count': len(inventory_rows),
                    'columns': ['APP ID', 'Application', 'Repo', 'Primary Language', 'Framework', 'LOC (K)', 'Modules', 'DB', 'Ext Int', 'Quality', 'Security', 'Cloud Ready'],
                    'data': inventory_rows[:20] if inventory_rows else [],  # First 20 rows for preview
                    'total': len(inventory_rows)
                },
                'application_classification': {
                    'label': 'Application Classification',
                    'count': len(classification_rows),
                    'columns': ['APP ID', 'Application', 'Business owner', 'Application Type', 'Install Type', 'Capabilities'],
                    'data': classification_rows[:20] if classification_rows else [],  # First 20 rows for preview
                    'total': len(classification_rows)
                },
                'internal_architecture': {
                    'label': 'Internal Architecture',
                    'count': len(architecture_rows),
                    'columns': ['APP ID', 'Application', 'Module', 'Layer', 'Language', 'DB Calls', 'External Calls', 'App Type', 'Install Type'],
                    'data': architecture_rows[:20] if architecture_rows else [],  # First 20 rows for preview
                    'total': len(architecture_rows)
                },
                'high_risk_applications': {
                    'label': 'High-Risk Applications',
                    'count': len(high_risk_rows),
                    'columns': ['Rank', 'APP ID', 'Application', 'Risk', 'Quality', 'Security', 'Cloud', 'App Type', 'Install Type', 'Capabilities'],
                    'data': high_risk_rows[:20] if high_risk_rows else [],  # First 20 rows for preview
                    'total': len(high_risk_rows)
                }
            },
            'extracted_rows': {
                'app_inventory': len(inventory_rows),
                'app_classification': len(classification_rows),
                'internal_architecture': len(architecture_rows),
                'high_risk_applications': len(high_risk_rows),
                'total': len(inventory_rows) + len(classification_rows) + len(architecture_rows) + len(high_risk_rows)
            }
        }), 201
    
    except FileNotFoundError as e:
        logger.error(f"[CAST Extract] File not found: {str(e)}", exc_info=True)
        return jsonify({'error': f'File not found: {str(e)}'}), 404
    except Exception as e:
        logger.error(f"[CAST Extract] Error: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'CAST extraction failed: {str(e)}'}), 500


@bp.route('/infrastructure/<file_id>/discovered-apps', methods=['GET'])
def get_discovered_applications(file_id):
    """Get discovered applications for an infrastructure file with pagination"""
    try:
        # Parse pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        infra = Infrastructure.query.filter_by(file_id=file_id).first()
        if not infra:
            return jsonify({'error': 'Infrastructure file not found'}), 404
        
        # Get paginated results
        paginated_apps = InfrastructureDiscovery.query.filter_by(
            infrastructure_id=infra.id
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        apps_data = [app.to_dict() for app in paginated_apps.items]
        
        return jsonify({
            'infrastructure_id': infra.id,
            'file_id': file_id,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated_apps.total,
                'pages': paginated_apps.pages,
                'has_next': paginated_apps.has_next,
                'has_prev': paginated_apps.has_prev
            },
            'applications': apps_data
        }), 200
        
    except Exception as e:
        logger.error(f"[Get Discovered Apps] Error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error retrieving applications: {str(e)}'}), 500


@bp.route('/reports/pdf', methods=['GET'])
def list_pdf_reports():
    """List all extracted PDF reports"""
    try:
        report_type = request.args.get('type')
        
        if report_type:
            reports = PDFExtractionService.get_reports_by_type(report_type)
        else:
            reports = PDFReport.query.all()
        
        return jsonify({
            'reports': [r.to_dict() for r in reports],
            'total': len(reports)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error listing reports: {str(e)}'}), 500


@bp.route('/reports/pdf/<int:report_id>', methods=['GET'])
def get_pdf_report(report_id):
    """Get a specific PDF report"""
    try:
        report = PDFExtractionService.get_report(report_id)
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        return jsonify(report.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Error retrieving report: {str(e)}'}), 500


@bp.route('/reports/pdf/search', methods=['GET'])
def search_pdf_reports():
    """Search in PDF reports"""
    try:
        query = request.args.get('q')
        report_type = request.args.get('type')
        
        if not query:
            return jsonify({'error': 'Query parameter required'}), 400
        
        results = PDFExtractionService.search_in_reports(query, report_type)
        
        return jsonify({
            'query': query,
            'results': [r.to_dict() for r in results],
            'total': len(results)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Search failed: {str(e)}'}), 500


@bp.route('/business-capabilities/import', methods=['POST'])
def import_business_capabilities():
    """Import Business Capabilities from TestData_RussianOwners.xlsx"""
    try:
        excel_path = 'data/TestData_RussianOwners.xlsx'
        
        if not os.path.exists(excel_path):
            return jsonify({'error': f'Excel file not found: {excel_path}'}), 404
        
        logger.info(f"[Upload] Importing Business Capabilities from {excel_path}")
        
        # Import the data
        result = BusinessCapabilitiesService.import_from_excel(excel_path)
        
        return jsonify({
            'success': True,
            'message': 'Business Capabilities imported successfully',
            'stats': result
        }), 201
    
    except Exception as e:
        logger.error(f"[Upload] Error importing business capabilities: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Import failed: {str(e)}'}), 500


@bp.route('/business-capabilities', methods=['GET'])
def get_business_capabilities():
    """Get all business capabilities"""
    try:
        capabilities = BusinessCapabilitiesService.get_all()
        
        return jsonify({
            'success': True,
            'capabilities': [c.to_dict() for c in capabilities],
            'total': len(capabilities)
        }), 200
    
    except Exception as e:
        logger.error(f"[Upload] Error retrieving business capabilities: {str(e)}")
        return jsonify({'error': f'Retrieval failed: {str(e)}'}), 500


@bp.route('/business-capabilities/<app_id>', methods=['GET'])
def get_business_capability(app_id):
    """Get business capability by APP ID"""
    try:
        capability = BusinessCapabilitiesService.get_by_app_id(app_id)
        
        if not capability:
            return jsonify({'error': f'Business Capability not found for APP ID: {app_id}'}), 404
        
        return jsonify({
            'success': True,
            'capability': capability.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"[Upload] Error retrieving business capability: {str(e)}")
        return jsonify({'error': f'Retrieval failed: {str(e)}'}), 500


@bp.route('/business-capabilities/search', methods=['GET'])
def search_business_capabilities():
    """Search business capabilities"""
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        results = BusinessCapabilitiesService.search(query)
        
        return jsonify({
            'success': True,
            'query': query,
            'results': [r.to_dict() for r in results],
            'total': len(results)
        }), 200
    
    except Exception as e:
        logger.error(f"[Upload] Error searching business capabilities: {str(e)}")
        return jsonify({'error': f'Search failed: {str(e)}'}), 500


@bp.route('/industry-templates', methods=['POST'])
def upload_industry_templates():
    """Upload Industry Templates file (Excel)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Only PDF, XLSX, and CSV files are supported'}), 400
    
    try:
        filename = secure_filename(file.filename)
        upload_folder = get_upload_folder()
        filepath = os.path.join(upload_folder, filename)
        
        file.save(filepath)
        logger.info(f"[Industry Templates] File saved to {filepath}")
        
        # Determine file type
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext in ['xlsx', 'xls']:
            # Extract data from Excel file
            file_id, template, records_count, errors = IndustryDataService.extract_from_excel(filepath, filename)
            
            return jsonify({
                'success': True,
                'file_id': file_id,
                'filename': filename,
                'template': template.to_dict(),
                'records_imported': records_count,
                'errors': errors if errors else None
            }), 201
        else:
            return jsonify({'error': f'Unsupported file type: {file_ext}. Please upload an Excel file (.xlsx or .xls)'}), 400
    
    except Exception as e:
        logger.error(f"[Industry Templates] Error uploading file: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/industry-templates/files', methods=['GET'])
def get_industry_templates():
    """Get all industry template files with record counts"""
    try:
        templates = IndustryDataService.get_templates_with_count()
        
        return jsonify({
            'success': True,
            'templates': templates,
            'total': len(templates)
        }), 200
    
    except Exception as e:
        logger.error(f"[Industry Templates] Error retrieving templates: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/industry-templates/<file_id>/data', methods=['GET'])
def get_industry_data(file_id):
    """Get industry data for a specific template file"""
    try:
        # Find template by file_id
        template = IndustryTemplate.query.filter_by(file_id=file_id).first()
        
        if not template:
            return jsonify({'error': 'Template file not found'}), 404
        
        # Get data with pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        paginated_data = IndustryData.query.filter_by(
            template_id=template.id
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        data = [record.to_dict() for record in paginated_data.items]
        
        return jsonify({
            'success': True,
            'template': template.to_dict(),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated_data.total,
                'pages': paginated_data.pages,
                'has_next': paginated_data.has_next,
                'has_prev': paginated_data.has_prev
            },
            'data': data
        }), 200
    
    except Exception as e:
        logger.error(f"[Industry Templates] Error retrieving data: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/industry-templates/<file_id>', methods=['DELETE'])
def delete_industry_template(file_id):
    """Delete an industry template file and all associated data"""
    try:
        template = IndustryTemplate.query.filter_by(file_id=file_id).first()
        
        if not template:
            return jsonify({'error': 'Template file not found'}), 404
        
        records_deleted = IndustryDataService.delete_template(template.id)
        
        return jsonify({
            'success': True,
            'message': 'Industry template deleted successfully',
            'records_deleted': records_deleted
        }), 200
    
    except Exception as e:
        logger.error(f"[Industry Templates] Error deleting template: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/industry-templates/preview/<file_id>', methods=['GET'])
def preview_industry_template(file_id):
    """Get preview of industry template file (first 20 rows)"""
    try:
        template = IndustryTemplate.query.filter_by(file_id=file_id).first()
        
        if not template:
            return jsonify({'error': 'Template file not found'}), 404
        
        # Get first 20 records
        records = IndustryData.query.filter_by(
            template_id=template.id
        ).limit(20).all()
        
        preview_data = [record.to_dict() for record in records]
        
        # Get column information
        columns = [
            'APP ID',
            'APP Name',
            'Business owner',
            'Architecture type',
            'Platform Host',
            'Application type',
            'Install type',
            'Capabilities'
        ]
        
        return jsonify({
            'success': True,
            'template': template.to_dict(),
            'columns': columns,
            'preview_data': preview_data,
            'total_records': IndustryData.query.filter_by(template_id=template.id).count()
        }), 200
    
    except Exception as e:
        logger.error(f"[Industry Templates] Error previewing template: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
