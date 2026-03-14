import json
import uuid
import logging
from pypdf import PdfReader
from app.models.code import CodeRepository, ArchitectureComponent, InternalDependency
from app.models.application import Application
from app import db

logger = logging.getLogger(__name__)

class CASTService:
    """Service for extracting code intelligence from CAST analysis"""
    
    @staticmethod
    def extract_from_pdf(file_path, file_name):
        """Extract code intelligence data from PDF file"""
        try:
            logger.info(f"[CASTService] Starting PDF extraction from {file_path}")
            pdf_reader = PdfReader(file_path)
            logger.info(f"[CASTService] PDF loaded successfully, pages: {len(pdf_reader.pages)}")
            
            text = ""
            for i, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    text += page_text
                    logger.debug(f"[CASTService] Extracted text from page {i+1}")
                except Exception as page_error:
                    logger.warning(f"[CASTService] Error extracting text from page {i+1}: {str(page_error)}")
            
            if not text.strip():
                raise Exception("No text could be extracted from PDF - file may be empty or image-based")
            
            logger.info(f"[CASTService] Total text extracted: {len(text)} characters")
            return CASTService.parse_code_data(text, file_name, file_path)
        except Exception as e:
            logger.error(f"[CASTService] Error reading PDF: {str(e)}", exc_info=True)
            raise Exception(f"Error reading PDF: {str(e)}")
    
    @staticmethod
    def parse_code_data(text, file_name, file_path=None):
        """Parse extracted text to create code entities"""
        file_id = str(uuid.uuid4())
        
        # Create CodeRepository record
        repo = CodeRepository(
            file_id=file_id,
            filename=file_name,
            repo_url='git.company.com/analysis',
            repo_name=file_name.replace('.pdf', ''),
            language='Multiple',
            framework='Various',
            primary_tech='Multi-stack',
            file_path=file_path
        )
        
        db.session.add(repo)
        db.session.flush()
        
        # Parse applications from code data
        apps_data = CASTService._extract_applications(text)
        for app_data in apps_data:
            # Check if application already exists
            existing_app = Application.query.filter_by(app_name=app_data['name']).first()
            
            if existing_app:
                # Update existing application with new data
                logger.info(f"[CASTService] Application '{app_data['name']}' already exists. Updating record.")
                existing_app.environment = app_data['environment']
                existing_app.technology_stack = json.dumps(app_data.get('techs', []))
                existing_app.version = app_data.get('version', '1.0')
                existing_app.deployment_path = app_data.get('deployment_path')
                existing_app.server_install_directory = app_data.get('install_dir')
                existing_app.repository_id = repo.id
                existing_app.description = app_data.get('description', '')
                app = existing_app
            else:
                # Create new application
                app = Application(
                    app_name=app_data['name'],
                    environment=app_data['environment'],
                    technology_stack=json.dumps(app_data.get('techs', [])),
                    version=app_data.get('version', '1.0'),
                    deployment_path=app_data.get('deployment_path'),
                    server_install_directory=app_data.get('install_dir'),
                    repository_id=repo.id,
                    description=app_data.get('description', '')
                )
                db.session.add(app)
            
            db.session.flush()
            
            # Parse architecture components
            components_data = app_data.get('components', [])
            for comp_data in components_data:
                component = ArchitectureComponent(
                    repository_id=repo.id,
                    component_name=comp_data['name'],
                    component_type=comp_data.get('type'),
                    description=comp_data.get('description'),
                    file_path=comp_data.get('path')
                )
                db.session.add(component)
            
            # Parse dependencies
            deps_data = app_data.get('dependencies', [])
            for dep_data in deps_data:
                dependency = InternalDependency(
                    repository_id=repo.id,
                    source_component=dep_data.get('source'),
                    target_component=dep_data.get('target'),
                    dependency_type=dep_data.get('type'),
                    external_api=dep_data.get('external_api')
                )
                db.session.add(dependency)
        
        db.session.commit()
        return file_id, repo
    
    @staticmethod
    def _extract_applications(text):
        """Extract application information from text"""
        # This would parse actual application data
        # For demo, returning sample applications
        return [
            {
                'name': 'InventoryAPI',
                'environment': 'prd',
                'techs': ['.NET', 'PostgreSQL', 'REST API'],
                'version': '2.1.0',
                'deployment_path': '/apps/inventory',
                'install_dir': '/opt/inventory',
                'description': 'Core inventory management API',
                'components': [
                    {'name': 'StockController', 'type': 'Controller', 'path': 'Controllers/StockController.cs'},
                    {'name': 'StockService', 'type': 'Service', 'path': 'Services/StockService.cs'},
                    {'name': 'StockRepository', 'type': 'Repository', 'path': 'Repositories/StockRepository.cs'},
                ],
                'dependencies': [
                    {'source': 'StockController', 'target': 'StockService', 'type': 'Calls'},
                    {'source': 'StockService', 'target': 'PostgreSQL', 'type': 'Depends'},
                    {'source': 'StockService', 'target': 'External ERP API', 'type': 'Calls', 'external_api': 'SAP'},
                ]
            },
            {
                'name': 'MfgExecutionService',
                'environment': 'prd',
                'techs': ['.NET Framework', 'SQL Server', 'SOAP'],
                'version': '1.8.5',
                'deployment_path': '/apps/mfg',
                'install_dir': '/opt/mfg',
                'description': 'Manufacturing execution system',
                'components': [
                    {'name': 'OrderController', 'type': 'Controller', 'path': 'Controllers/OrderController.cs'},
                    {'name': 'OrderService', 'type': 'Service', 'path': 'Services/OrderService.cs'},
                ],
                'dependencies': [
                    {'source': 'OrderController', 'target': 'OrderService', 'type': 'Calls'},
                    {'source': 'OrderService', 'target': 'SQL Server', 'type': 'Depends'},
                ]
            },
            {
                'name': 'FinanceLedgerApp',
                'environment': 'dev',
                'techs': ['Java 11', 'Oracle Database', 'Spring Boot'],
                'version': '3.0.1',
                'deployment_path': '/apps/finance',
                'install_dir': '/opt/finance',
                'description': 'Financial ledger management application',
                'components': [
                    {'name': 'LedgerController', 'type': 'Controller', 'path': 'controllers/LedgerController.java'},
                    {'name': 'LedgerService', 'type': 'Service', 'path': 'services/LedgerService.java'},
                ],
                'dependencies': [
                    {'source': 'LedgerController', 'target': 'LedgerService', 'type': 'Calls'},
                    {'source': 'LedgerService', 'target': 'Oracle Database', 'type': 'Depends'},
                ]
            }
        ]
    
    @staticmethod
    def get_repository_summary(repo_id):
        """Get summary statistics for code repository"""
        repo = CodeRepository.query.get(repo_id)
        if not repo:
            return None
        
        return {
            'repo_name': repo.repo_name,
            'primary_tech': repo.primary_tech,
            'total_components': len(repo.components),
            'total_dependencies': len(repo.dependencies),
            'applications': [app.app_name for app in repo.applications],
            'technologies': list(set([app.technology_stack for app in repo.applications]))
        }
