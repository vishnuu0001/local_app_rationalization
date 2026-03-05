from flask import Blueprint, request, jsonify
from app import db
from app.services.capability_service import CapabilityService
from app.services.rationalization_service import RationalizationService
from app.services.insight_service import InsightService
from app.services.data_initialization_service import DataInitializationService
from app.services.excel_data_loader_service import ExcelDataLoaderService
from app.services.standardization_analysis_service import StandardizationAnalysisService
from app.models.capability import BusinessCapability, CapabilityMapping
from app.models.analysis import RationalizationScenario

bp = Blueprint('visualization', __name__, url_prefix='/api')

@bp.route('/capabilities', methods=['GET'])
def get_capabilities():
    """Get all business capabilities with applications"""
    capabilities = CapabilityService.get_all_capabilities()
    
    return jsonify({
        'capabilities': capabilities,
        'total': len(capabilities)
    }), 200

@bp.route('/capability/<int:capability_id>', methods=['GET'])
def get_capability(capability_id):
    """Get specific capability with applications"""
    capability = CapabilityService.get_capability_with_applications(capability_id)
    
    if not capability:
        return jsonify({'error': 'Capability not found'}), 404
    
    return jsonify(capability), 200

@bp.route('/capability/by-name/<name>', methods=['GET'])
def get_capability_by_name(name):
    """Get capability by name"""
    capability = BusinessCapability.query.filter_by(capability_name=name).first()
    
    if not capability:
        return jsonify({'error': 'Capability not found'}), 404
    
    result = CapabilityService.get_capability_with_applications(capability.id)
    return jsonify(result), 200

@bp.route('/capability-map', methods=['POST'])
def create_capability_mapping():
    """Map application to capability"""
    data = request.get_json()
    
    try:
        mapping = CapabilityService.map_application_to_capability(
            data.get('capability_id'),
            data.get('application_name'),
            data.get('technology'),
            data.get('erp_overlap'),
            data.get('redundancy_level', 'None'),
            data.get('criticality', 'Medium'),
            data.get('owner_team'),
            data.get('maintenance_cost', 0.0)
        )
        
        return jsonify(mapping.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/rationalization-scenarios', methods=['GET'])
def get_rationalization_scenarios():
    """Get all rationalization scenarios"""
    scenarios = RationalizationService.get_all_scenarios()
    
    return jsonify({
        'scenarios': scenarios,
        'total': len(scenarios)
    }), 200

@bp.route('/rationalization-scenario/<int:scenario_id>', methods=['GET'])
def get_rationalization_scenario(scenario_id):
    """Get specific rationalization scenario"""
    scenario = RationalizationService.get_scenario(scenario_id)
    
    if not scenario:
        return jsonify({'error': 'Scenario not found'}), 404
    
    return jsonify(scenario), 200

@bp.route('/rationalization-scenarios/by-capability/<capability>', methods=['GET'])
def get_scenarios_by_capability(capability):
    """Get scenarios for specific capability"""
    scenarios = RationalizationService.get_scenarios_by_capability(capability)
    
    return jsonify({
        'scenarios': scenarios,
        'capability': capability,
        'total': len(scenarios)
    }), 200

@bp.route('/rationalization-scenario', methods=['POST'])
def create_rationalization_scenario():
    """Create new rationalization scenario"""
    data = request.get_json()
    
    try:
        scenario = RationalizationService.create_scenario(
            data.get('scenario_name'),
            data.get('description'),
            data.get('capability'),
            data.get('before_state'),
            data.get('after_state'),
            data.get('metrics'),
            data.get('target_erp'),
            data.get('timeline_months')
        )
        
        return jsonify(scenario.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/dashboard', methods=['GET'])
def get_dashboard_data():
    """
    Get comprehensive dashboard data with insights.
    
    Returns:
    - If correlation exists: complete correlation-based data
    - Otherwise: insights from available data sources (Corent, CAST, ApplicationInventory)
    - Recommendations based on current state
    """
    try:
        insights = InsightService.get_dashboard_insights()
        
        return jsonify({
            'status': 'success',
            'data': insights,
            'summary': insights['summary'],
            'recommendations': insights['recommendations'],
            'data_sources': insights['data_sources']
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get dashboard data: {str(e)}'
        }), 500

@bp.route('/traceability-matrix', methods=['GET'])
def get_traceability_matrix():
    """Get complete traceability matrix"""
    from app.models.infrastructure import Server
    from app.models.application import Application
    from app.models.code import CodeRepository
    
    matrix = []
    
    servers = Server.query.all()
    for server in servers:
        apps = Application.query.all()
        
        for app in apps:
            capability = BusinessCapability.query.join(CapabilityMapping).filter(
                CapabilityMapping.application_name == app.app_name
            ).first()
            
            duplicates = CapabilityMapping.query.filter(
                CapabilityMapping.capability_id == capability.id if capability else -1
            ).count()
            
            matrix.append({
                'infrastructure': server.server_name,
                'application': app.app_name,
                'repository': app.repository_id,
                'capability': capability.capability_name if capability else 'Unmapped',
                'redundancy': 'Duplicate' if duplicates > 1 else 'Unique',
                'action': 'Migrate' if duplicates > 1 else 'Retain'
            })
    
    return jsonify({
        'matrix': matrix,
        'total_rows': len(matrix)
    }), 200

@bp.route('/initialize-defaults', methods=['POST'])
def initialize_defaults():
    """Initialize default capabilities and scenarios"""
    try:
        CapabilityService.initialize_default_capabilities()
        RationalizationService.initialize_default_scenarios()
        
        return jsonify({
            'success': True,
            'message': 'Default data initialized'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/initialize-test-data', methods=['POST'])
def initialize_test_data():
    """Initialize test/demo data for rapid development (only if database is empty)"""
    try:
        # Check if data already exists
        from app.models.corent_data import CorentData
        from app.models.cast import CASTData
        
        corent_count = CorentData.query.count()
        cast_count = CASTData.query.count()
        
        if corent_count > 0 or cast_count > 0:
            return jsonify({
                'status': 'info',
                'message': 'Database already contains data. Skipping test data initialization.',
                'reason': f'Corent records: {corent_count}, CAST records: {cast_count}',
                'action': 'To reset data, delete the database file and run init_db.py again'
            }), 200
        
        result = DataInitializationService.initialize_test_data()
        
        return jsonify({
            'status': 'success',
            'message': result['message'],
            'data_initialized': {
                'corent_items': result['corent_items'],
                'cast_items': result['cast_items'],
                'app_inventory_items': result['app_inventory_items']
            },
            'next_step': 'Run correlation to link infrastructure and code data',
            'correlation_endpoint': '/api/correlation/start'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to initialize test data: {str(e)}'
        }), 500


@bp.route('/initialization-status', methods=['GET'])
def get_initialization_status():
    """Check database initialization status"""
    try:
        status = DataInitializationService.get_initialization_status()
        
        return jsonify({
            'status': 'success',
            **status
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get initialization status: {str(e)}'
        }), 500

@bp.route('/load-excel-data', methods=['POST'])
def load_excel_data():
    """Load production data from CORENT and CAST Excel files"""
    try:
        result = ExcelDataLoaderService.load_all_data()
        
        return jsonify({
            'status': 'success',
            'message': f"Loaded {result['total']} records from Excel",
            'data_loaded': {
                'corent_records': result['corent_loaded'],
                'cast_records': result['cast_loaded'],
                'total_records': result['total']
            },
            'next_step': 'Dashboard will now display the actual production data',
            'dashboard_endpoint': '/api/dashboard'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to load Excel data: {str(e)}'
        }), 500

@bp.route('/standardization-analysis/clear', methods=['DELETE'])
def clear_standardization_data():
    """Clear CorentData and CASTData used by the Standardization page."""
    try:
        from app.models.corent_data import CorentData
        from app.models.cast import CASTData

        corent_rows = CorentData.query.delete()
        cast_rows = CASTData.query.delete()
        db.session.execute(db.text('DELETE FROM server_application'))
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Standardization data cleared',
            'deleted': {
                'corent_data': corent_rows,
                'cast_data': cast_rows,
                'server_application': 'cleared'
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/standardization-analysis', methods=['GET'])
def get_standardization_analysis():
    """Get comprehensive standardization and consolidation analysis"""
    try:
        analysis = StandardizationAnalysisService.analyze_all_data()
        
        return jsonify({
            'status': 'success',
            'analysis': analysis,
            'generated_at': '2026-02-25T10:39:00Z'
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to generate standardization analysis: {str(e)}'
        }), 500