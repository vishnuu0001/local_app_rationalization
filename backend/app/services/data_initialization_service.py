"""
Data Initialization Service - Populates test/demo data for rapid prototyping

This service initializes a comprehensive set of test data that mimics real-world
scenarios with infrastructure (Corent), code analysis (CAST), and application
inventory information.
"""

from app import db
from app.models.corent_data import CorentData
from app.models.cast import CASTData, ApplicationInventory


class DataInitializationService:
    """Service to initialize test data for demonstration and development"""
    
    @staticmethod
    def initialize_test_data():
        """
        Initialize comprehensive test data covering:
        - Infrastructure applications (Corent)
        - Code analysis (CAST)
        """
        # Clear existing data
        db.session.query(ApplicationInventory).delete()
        db.session.query(CASTData).delete()
        db.session.query(CorentData).delete()
        db.session.commit()
        
        # Initialize Corent data (Infrastructure)
        corent_data = [
            CorentData(
                app_id='APP001',
                app_name='Inventory Management System',
                architecture_type='3-tier',
                business_owner='Supply Chain',
                platform_host='VM-PROD-01',
                server_type='Linux - CentOS 7',
                operating_system='CentOS 7',
                environment='Production',
                deployment_geography='EU-WEST-1',
                cloud_suitability='High',
                ha_dr_requirements='Active-Active',
                application_stability='Stable',
                volume_external_dependencies='8'
            ),
            CorentData(
                app_id='APP002',
                app_name='Customer Portal',
                architecture_type='2-tier Web',
                business_owner='Sales',
                platform_host='VM-PROD-02',
                server_type='Windows Server 2019',
                operating_system='Windows Server 2019',
                environment='Production',
                deployment_geography='EU-CENTRAL-1',
                cloud_suitability='Medium',
                ha_dr_requirements='Warm Standby',
                application_stability='Good',
                volume_external_dependencies='12'
            ),
            CorentData(
                app_id='APP003',
                app_name='Financial Reporting',
                architecture_type='3-tier',
                business_owner='Finance',
                platform_host='VM-PROD-03',
                server_type='Oracle Database',
                operating_system='Linux - RHEL 8',
                environment='Production',
                deployment_geography='EU-WEST-1',
                cloud_suitability='Medium',
                ha_dr_requirements='Active-Passive',
                application_stability='Stable',
                volume_external_dependencies='5'
            ),
            CorentData(
                app_id='APP004',
                app_name='Legacy ERP System',
                architecture_type='Mainframe',
                business_owner='Operations',
                platform_host='MAINFRAME-01',
                server_type='Mainframe - Deprecated',
                operating_system='z/OS',
                environment='Production',
                deployment_geography='ON-PREMISE',
                cloud_suitability='Low',
                ha_dr_requirements='Manual',
                application_stability='Unstable',
                volume_external_dependencies='25'
            ),
            CorentData(
                app_id='APP005',
                app_name='Analytics Dashboard',
                architecture_type='Web',
                business_owner='Analytics',
                platform_host='VM-PROD-05',
                server_type='Linux - Ubuntu 20.04',
                operating_system='Ubuntu 20.04',
                environment='Production',
                deployment_geography='EU-WEST-1',
                cloud_suitability='High',
                ha_dr_requirements='None',
                application_stability='Good',
                volume_external_dependencies='6'
            ),
            CorentData(
                app_id='LEGACY001',
                app_name='Legacy Document Manager',
                architecture_type='Monolith',
                business_owner='Document Management',
                platform_host='LEGACY-SERVER-01',
                server_type='Windows Server 2003',
                operating_system='Windows Server 2003',
                environment='Production',
                deployment_geography='ON-PREMISE',
                cloud_suitability='Not Suitable',
                ha_dr_requirements='None',
                application_stability='Unstable',
                volume_external_dependencies='15'
            ),
        ]
        
        db.session.add_all(corent_data)
        db.session.commit()
        
        # Initialize CAST data (Code Analysis)
        cast_data = [
            CASTData(
                app_id='APP001',
                app_name='Inventory Management System',
                application_architecture='Microservices',
                source_code_availability='Available',
                programming_language='Python',
                component_coupling='3.2',
                cloud_suitability='Cloud Native',
                volume_external_dependencies='8',
                code_design='Good'
            ),
            CASTData(
                app_id='APP002',
                app_name='Customer Portal',
                application_architecture='MVC',
                source_code_availability='Partial',
                programming_language='JavaScript/Node.js',
                component_coupling='4.5',
                cloud_suitability='Cloud Optimized',
                volume_external_dependencies='12',
                code_design='Fair'
            ),
            CASTData(
                app_id='APP003',
                app_name='Financial Reporting',
                application_architecture='N-tier',
                source_code_availability='Available',
                programming_language='Java',
                component_coupling='2.8',
                cloud_suitability='Cloud Ready',
                volume_external_dependencies='5',
                code_design='Excellent'
            ),
            CASTData(
                app_id='APP004',
                app_name='Legacy ERP System',
                application_architecture='Monolith',
                source_code_availability='Not Available',
                programming_language='COBOL',
                component_coupling='8.2',
                cloud_suitability='Not Cloud Ready',
                volume_external_dependencies='25',
                code_design='Poor'
            ),
            CASTData(
                app_id='APP005',
                app_name='Analytics Dashboard',
                application_architecture='React/Dashboards',
                source_code_availability='Available',
                programming_language='JavaScript/React',
                component_coupling='2.1',
                cloud_suitability='Cloud Native',
                volume_external_dependencies='6',
                code_design='Good'
            ),
            CASTData(
                app_id='DEV001',
                app_name='Development Analytics',
                application_architecture='Lambda/Serverless',
                source_code_availability='Available',
                programming_language='Python',
                component_coupling='1.5',
                cloud_suitability='Cloud Native',
                volume_external_dependencies='3',
                code_design='Excellent'
            ),
        ]
        
        db.session.add_all(cast_data)
        db.session.commit()
        
        return {
            'status': 'success',
            'message': 'Test data initialized successfully',
            'corent_items': len(corent_data),
            'cast_items': len(cast_data),
            'app_inventory_items': 0
        }
    
    @staticmethod
    def get_initialization_status():
        """Check if database needs initialization"""
        corent_count = db.session.query(CorentData).count()
        cast_count = db.session.query(CASTData).count()
        app_inv_count = db.session.query(ApplicationInventory).count()
        
        return {
            'needs_initialization': (corent_count == 0 or cast_count == 0),
            'corent_items': corent_count,
            'cast_items': cast_count,
            'app_inventory_items': app_inv_count,
            'data_ready': corent_count > 0 and cast_count > 0
        }
