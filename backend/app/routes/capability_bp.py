"""
Business Capability Routes
Endpoints for capability mapping and analysis
"""

from flask import Blueprint, request, jsonify
from app.services.business_capability_service import BusinessCapabilityService

capability_bp = Blueprint('capability', __name__, url_prefix='/api/capability')


@capability_bp.route('/mapping', methods=['GET'])
def get_capability_mapping():
    """Get paginated application-to-capability mappings"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        result = BusinessCapabilityService.get_capability_application_mapping(
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@capability_bp.route('/analysis', methods=['GET'])
def get_capability_analysis():
    """Get capability analysis with consolidation candidates"""
    try:
        result = BusinessCapabilityService.get_capability_analysis()
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@capability_bp.route('/details/<capability_name>', methods=['GET'])
def get_capability_details(capability_name):
    """Get detailed view of applications for a specific capability"""
    try:
        result = BusinessCapabilityService.get_capability_details(capability_name)
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@capability_bp.route('/export', methods=['GET'])
def export_capability_mapping():
    """Export complete capability mapping"""
    try:
        format_type = request.args.get('format', 'json', type=str)
        
        result = BusinessCapabilityService.get_capability_mapping_export(format_type)
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
