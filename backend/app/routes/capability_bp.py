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
    from app import db
    from app.models.industry_data import IndustryData
    from app.models.corent_data import CorentData
    
    try:
        # Query all industry apps
        industry_apps = db.session.query(IndustryData).filter(
            IndustryData.capabilities.isnot(None),
            IndustryData.capabilities != ''
        ).all()
        
        # Filter matching capability (simple substring match)
        applications = []
        for app in industry_apps:
            # Check if capability name appears in the capabilities field
            if capability_name.lower() in str(app.capabilities).lower():
                # Get CorentData install_type
                try:
                    corent_record = db.session.query(CorentData.install_type).filter(
                        CorentData.app_id == app.app_id
                    ).first()
                    install_type = corent_record.install_type if corent_record else 'N/A'
                except:
                    install_type = 'N/A'
                
                applications.append({
                    'app_id': app.app_id,
                    'app_name': app.app_name,
                    'business_owner': app.business_owner or 'Unknown',
                    'architecture_type': app.architecture_type or 'N/A',
                    'platform_host': app.platform_host or 'N/A',
                    'application_type': app.application_type or 'N/A',
                    'install_type': install_type,
                    'technology_stack': app.application_type or 'N/A'
                })
        
        # Build analysis
        if len(applications) > 1:
            tech_stacks = {}
            for app_dict in applications:
                tech = app_dict['technology_stack']
                if tech not in tech_stacks:
                    tech_stacks[tech] = []
                tech_stacks[tech].append(app_dict['app_name'])
            
            analysis = {
                'total_apps': len(applications),
                'is_elimination_candidate': True,
                'elimination_reason': f'{len(applications)} applications provide this capability',
                'technology_distribution': tech_stacks,
                'consolidation_summary': {
                    'apps_to_consolidate': len(applications),
                    'apps_to_eliminate': max(1, len(applications) - 1),
                    'consolidation_ratio': f'{len(applications)}:1'
                }
            }
        else:
            analysis = {
                'total_apps': len(applications),
                'is_elimination_candidate': False,
                'elimination_reason': None,
                'recommendation': 'No consolidation recommended' if len(applications) <= 1 else None
            }
        
        return jsonify({
            'status': 'success',
            'data': {
                'capability': capability_name,
                'analysis': analysis,
                'applications': applications
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500



@capability_bp.route('/debug/<capability_name>', methods=['GET'])
def debug_capability_details(capability_name):
    """DEBUG: Test the matching logic within Flask context"""
    from app import db
    from app.models.industry_data import IndustryData
    
    try:
        # Get industry apps
        industry_apps = db.session.query(
            IndustryData.app_id,
            IndustryData.app_name,
            IndustryData.capabilities
        ).filter(
            IndustryData.capabilities.isnot(None),
            IndustryData.capabilities != ''
        ).all()
        
        total_apps = len(industry_apps)
        
        # Test matching
        def normalize_cap(c):
            return c.strip().removesuffix(' (Provides)').removesuffix('(Provides)').strip().lower()
        
        normalized_requested = normalize_cap(capability_name)
        matched_count = 0
        matches = []
        
        for app in industry_apps:
            caps = [c.strip() for c in str(app.capabilities).split(',') if c.strip()]
            if capability_name in caps or any(normalize_cap(c) == normalized_requested for c in caps):
                matched_count += 1
                matches.append({
                    'app_id': app.app_id,
                    'app_name': app.app_name,
                    'caps': caps
                })
        
        return jsonify({
            'status': 'success',
            'capability_requested': capability_name,
            'capability_normalized': normalized_requested,
            'total_apps_in_db': total_apps,
            'matched_count': matched_count,
            'first_3_matches': matches[:3]
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500


@capability_bp.route('/clear', methods=['DELETE'])
def clear_capability_data():
    """Clear IndustryData and IndustryTemplate records (resets Capability Mapping page)"""
    try:
        from app import db
        from app.models.industry_data import IndustryData, IndustryTemplate
        rows = IndustryData.query.delete()
        templates = IndustryTemplate.query.delete()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Capability data cleared',
            'deleted': {'industry_data': rows, 'industry_templates': templates}
        }), 200
    except Exception as e:
        from app import db
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


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
