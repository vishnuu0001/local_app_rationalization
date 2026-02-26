from flask import Blueprint, request, jsonify
from app import db
from app.services.correlation_service import CorrelationService
from app.services.infrastructure_service import InfrastructureService
from app.services.cast_service import CASTService
from app.models.infrastructure import Infrastructure
from app.models.code import CodeRepository
from app.models.application import Application
from app.models.analysis import AnalysisResult

bp = Blueprint('analysis', __name__, url_prefix='/api/analysis')

@bp.route('/correlate', methods=['POST'])
def correlate_infra_and_code():
    """Correlate infrastructure and code intelligence"""
    data = request.get_json()
    infrastructure_id = data.get('infrastructure_id')
    repository_id = data.get('repository_id')
    
    if not infrastructure_id or not repository_id:
        return jsonify({'error': 'Missing infrastructure_id or repository_id'}), 400
    
    try:
        analysis_id, correlation, correlations = CorrelationService.correlate_infrastructure_and_code(
            infrastructure_id,
            repository_id
        )
        
        # Create analysis result
        analysis = AnalysisResult(
            analysis_id=analysis_id,
            analysis_type='Correlation',
            infrastructure_file_id=str(infrastructure_id),
            code_file_id=str(repository_id)
        )
        db.session.add(analysis)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'analysis_id': analysis_id,
            'match_score': correlation.match_score,
            'correlations': correlations,
            'summary': {
                'total_servers': len(set(c['server'] for c in correlations)),
                'total_applications': len(set(c['application'] for c in correlations)),
                'matched_pairs': len(correlations),
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/infrastructure/<int:infra_id>/summary', methods=['GET'])
def get_infrastructure_summary(infra_id):
    """Get infrastructure analysis summary"""
    summary = InfrastructureService.get_infrastructure_summary(infra_id)
    
    if not summary:
        return jsonify({'error': 'Infrastructure not found'}), 404
    
    return jsonify(summary), 200

@bp.route('/code/<int:repo_id>/summary', methods=['GET'])
def get_code_summary(repo_id):
    """Get code analysis summary"""
    summary = CASTService.get_repository_summary(repo_id)
    
    if not summary:
        return jsonify({'error': 'Repository not found'}), 404
    
    return jsonify(summary), 200

@bp.route('/applications', methods=['GET'])
def get_all_applications():
    """Get all applications"""
    apps = Application.query.all()
    
    return jsonify({
        'applications': [app.to_dict() for app in apps],
        'total': len(apps)
    }), 200

@bp.route('/infrastructure', methods=['GET'])
def get_all_infrastructure():
    """Get all infrastructure records"""
    infras = Infrastructure.query.all()
    
    return jsonify({
        'infrastructure': [inf.to_dict() for inf in infras],
        'total': len(infras)
    }), 200

@bp.route('/code-repositories', methods=['GET'])
def get_all_repositories():
    """Get all code repositories"""
    repos = CodeRepository.query.all()
    
    return jsonify({
        'repositories': [repo.to_dict() for repo in repos],
        'total': len(repos)
    }), 200

@bp.route('/analysis/<analysis_id>', methods=['GET'])
def get_analysis_result(analysis_id):
    """Get specific analysis result"""
    analysis = AnalysisResult.query.filter_by(analysis_id=analysis_id).first()
    
    if not analysis:
        return jsonify({'error': 'Analysis not found'}), 404
    
    return jsonify(analysis.to_dict()), 200

@bp.route('/analysis-history', methods=['GET'])
def get_analysis_history():
    """Get analysis history"""
    analyses = AnalysisResult.query.order_by(AnalysisResult.created_at.desc()).all()
    
    return jsonify({
        'analyses': [a.to_dict() for a in analyses],
        'total': len(analyses)
    }), 200
