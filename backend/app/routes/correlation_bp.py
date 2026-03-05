from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from app.services.correlation_service import CorrelationService
from app.models.correlation import CorrelationResult, MasterMatrixEntry
from app import db

correlation_bp = Blueprint('correlation', __name__, url_prefix='/api/correlation')


@correlation_bp.route('/start', methods=['POST'])
@cross_origin()
def start_correlation():
    """
    Trigger correlation between Corent and CAST extracted data.
    
    Returns:
        JSON with correlation results, dashboards, and master matrix
    """
    try:
        # Perform correlation
        correlation_data = CorrelationService.correlate_data()
        
        # Store in database
        result = CorrelationService.create_correlation_result(correlation_data)
        
        return jsonify({
            'status': 'success',
            'message': 'Correlation completed successfully',
            'correlation_id': result.id,
            'summary': {
                'matched_count': result.matched_count,
                'total_count': result.total_count,
                'match_percentage': result.match_percentage
            },
            'statistics': correlation_data.get('statistics', {}),
            'timestamp': result.created_at.isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Correlation failed: {str(e)}'
        }), 500


@correlation_bp.route('/latest', methods=['GET'])
@cross_origin()
def get_latest_correlation():
    """
    Get the latest correlation result with full data.
    
    Returns:
        JSON with complete correlation data and master matrix
    """
    try:
        # Get latest correlation result
        result = CorrelationResult.query.order_by(CorrelationResult.created_at.desc()).first()
        
        if not result:
            return jsonify({
                'status': 'empty',
                'message': 'No correlation results found. Run correlation first.',
                'correlation': None,
                'corent_dashboard': {
                    'server_app_mapping': [],
                    'tech_stack': {},
                    'deployment_footprint': {},
                    'total_applications': 0,
                    'total_servers': 0
                },
                'cast_dashboard': {
                    'repo_app_mapping': [],
                    'architecture_components': [],
                    'internal_dependencies': {},
                    'total_applications': 0,
                    'total_components': 0
                },
                'correlation_layer': [],
                'unmatched_corent': [],
                'unmatched_cast': [],
                'master_matrix': [],
                'statistics': {}
            }), 200
        
        import json
        
        correlation_data = json.loads(result.correlation_data) if isinstance(result.correlation_data, str) else result.correlation_data
        
        # Get fresh dashboard data from services
        corent_data = CorrelationService.get_corent_data()
        cast_data = CorrelationService.get_cast_data()
        
        # Regenerate master matrix with fresh data to ensure all fields are populated correctly
        fresh_master_matrix = CorrelationService.generate_master_matrix(correlation_data)
        
        return jsonify({
            'status': 'success',
            'correlation': {
                'id': result.id,
                'created_at': result.created_at.isoformat(),
                'matched_count': result.matched_count,
                'total_count': result.total_count,
                'match_percentage': result.match_percentage
            },
            'corent_dashboard': {
                'server_app_mapping': corent_data['server_app_mapping'],
                'tech_stack': corent_data['tech_stack'],
                'deployment_footprint': corent_data['deployment_footprint'],
                'total_applications': len(corent_data['server_app_mapping']),
                'total_servers': len(corent_data['server_list'])
            },
            'cast_dashboard': {
                'repo_app_mapping': cast_data['repo_app_mapping'],
                'architecture_components': cast_data['architecture_components'],
                'internal_dependencies': cast_data['internal_dependencies'],
                'total_applications': cast_data['total_items'],
                'total_components': len(cast_data['architecture_components'])
            },
            'correlation_layer': correlation_data.get('correlation_layer', []),
            'unmatched_corent': correlation_data.get('unmatched_corent', []),
            'unmatched_cast': correlation_data.get('unmatched_cast', []),
            'master_matrix': fresh_master_matrix,
            'statistics': correlation_data.get('statistics', {})
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve correlation: {str(e)}'
        }), 500


@correlation_bp.route('/dashboards', methods=['GET'])
@cross_origin()
def get_dashboards():
    """
    Get Corent and CAST dashboards separately.
    
    Returns:
        JSON with Corent dashboard (Server-App mapping, Tech stack, Deployment footprint)
        and CAST dashboard (Repo-App mapping, Dependencies, Components)
    """
    try:
        corent_data = CorrelationService.get_corent_data()
        cast_data = CorrelationService.get_cast_data()
        
        return jsonify({
            'status': 'success',
            'corent': {
                'title': 'Infrastructure Discovery (Corent)',
                'server_app_mapping': corent_data['server_app_mapping'],
                'tech_stack': corent_data['tech_stack'],
                'deployment_footprint': corent_data['deployment_footprint'],
                'total_applications': len(corent_data['server_app_mapping']),
                'total_servers': len(corent_data['server_list'])
            },
            'cast': {
                'title': 'Code Analysis (CAST)',
                'repo_app_mapping': cast_data['repo_app_mapping'],
                'architecture_components': cast_data['architecture_components'],
                'internal_dependencies': cast_data['internal_dependencies'],
                'total_applications': cast_data['total_items'],
                'total_components': len(cast_data['architecture_components'])
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve dashboards: {str(e)}'
        }), 500


@correlation_bp.route('/master-matrix', methods=['GET'])
@cross_origin()
def get_master_matrix():
    """
    Get the master matrix combining Corent and CAST data.
    
    Query parameters:
        - confidence_level (optional): 'high', 'medium', 'unmatched'
        - limit (optional): Number of rows to return (default: 1000)
        
    Returns:
        JSON with master matrix entries
    """
    try:
        limit = request.args.get('limit', 1000, type=int)
        confidence_level = request.args.get('confidence_level', None)
        
        # Get latest correlation
        result = CorrelationResult.query.order_by(CorrelationResult.created_at.desc()).first()
        
        if not result:
            return jsonify({
                'status': 'not_found',
                'message': 'No correlation results found. Run correlation first.'
            }), 404
        
        import json
        
        master_matrix = json.loads(result.master_matrix) if isinstance(result.master_matrix, str) else result.master_matrix
        
        # Filter by confidence level if specified
        if confidence_level:
            master_matrix = [m for m in master_matrix if m.get('confidence_level') == confidence_level]
        
        # Apply limit
        master_matrix = master_matrix[:limit]
        
        return jsonify({
            'status': 'success',
            'correlation_id': result.id,
            'created_at': result.created_at.isoformat(),
            'total_rows': len(json.loads(result.master_matrix) if isinstance(result.master_matrix, str) else result.master_matrix),
            'returned_rows': len(master_matrix),
            'columns': [
                'Infra',
                'Server',
                'Installed App',
                'App Component',
                'Repo',
                'Confidence'
            ],
            'data': master_matrix
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve master matrix: {str(e)}'
        }), 500


@correlation_bp.route('/statistics', methods=['GET'])
@cross_origin()
def get_statistics():
    """
    Get correlation statistics and summary.
    
    Returns:
        JSON with match statistics, unmatched items, confidence distribution
    """
    try:
        result = CorrelationResult.query.order_by(CorrelationResult.created_at.desc()).first()
        
        if not result:
            return jsonify({
                'status': 'not_found',
                'message': 'No correlation results found. Run correlation first.'
            }), 404
        
        import json
        from collections import Counter
        
        correlation_data = json.loads(result.correlation_data) if isinstance(result.correlation_data, str) else result.correlation_data
        
        # Calculate confidence distribution
        confidence_levels = [c.get('confidence_level') for c in correlation_data.get('correlation_layer', [])]
        confidence_dist = dict(Counter(confidence_levels))
        
        # Calculate unmatched percentages
        stored_stats = correlation_data.get('statistics', {})
        corent_total = stored_stats.get('corent_total', 0)
        cast_total = stored_stats.get('cast_total', 0)
        # Support both 'matched_count' and 'total_matched'/'direct_matched' key names
        matched = (stored_stats.get('matched_count') or
                   stored_stats.get('total_matched') or
                   stored_stats.get('direct_matched') or
                   result.matched_count or 0)
        
        unmatched_corent_pct = round((len(correlation_data.get('unmatched_corent', [])) / max(corent_total, 1)) * 100, 2)
        unmatched_cast_pct = round((len(correlation_data.get('unmatched_cast', [])) / max(cast_total, 1)) * 100, 2)
        
        return jsonify({
            'status': 'success',
            'summary': {
                'correlation_id': result.id,
                'created_at': result.created_at.isoformat(),
                'last_updated': result.updated_at.isoformat()
            },
            'statistics': {
                'corent_total': corent_total,
                'cast_total': cast_total,
                'matched_count': matched,
                'match_percentage': round((matched / max(corent_total, 1)) * 100, 2),
                'unmatched_corent': len(correlation_data.get('unmatched_corent', [])),
                'unmatched_corent_percentage': unmatched_corent_pct,
                'unmatched_cast': len(correlation_data.get('unmatched_cast', [])),
                'unmatched_cast_percentage': unmatched_cast_pct
            },
            'confidence_distribution': {
                'high': confidence_dist.get('high', 0),
                'medium': confidence_dist.get('medium', 0),
                'unmatched': confidence_dist.get('unmatched', 0)
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve statistics: {str(e)}'
        }), 500


@correlation_bp.route('/traceability/matrix', methods=['GET'])
@cross_origin()
def get_traceability_matrix():
    """
    Get complete traceability matrix with all applications mapped to infrastructure,
    capabilities, and recommended rationalization actions.
    
    Returns:
        JSON with full traceability data, summary statistics, and action breakdown
    """
    try:
        from app.services.traceability_service import TraceabilityService
        
        traceability_data = TraceabilityService.get_traceability_matrix()
        
        return jsonify({
            'status': 'success',
            'data': traceability_data['matrix'],
            'summary': traceability_data['summary'],
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve traceability matrix: {str(e)}'
        }), 500
