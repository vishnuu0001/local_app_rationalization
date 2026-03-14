from app import db
from datetime import datetime
import json

class AnalysisResult(db.Model):
    __tablename__ = 'analysis_results'
    
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.String(255), unique=True, nullable=False)
    analysis_type = db.Column(db.String(100), nullable=False)  # Infrastructure, CAST, Correlation
    infrastructure_file_id = db.Column(db.String(255))
    code_file_id = db.Column(db.String(255))
    status = db.Column(db.String(50), default='Completed')  # Pending, In Progress, Completed, Failed
    summary_data = db.Column(db.Text)  # JSON summary
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        summary = {}
        if self.summary_data:
            try:
                summary = json.loads(self.summary_data)
            except:
                summary = {}
        
        return {
            'id': self.id,
            'analysis_id': self.analysis_id,
            'analysis_type': self.analysis_type,
            'status': self.status,
            'summary_data': summary,
            'created_at': self.created_at.isoformat(),
        }

class RationalizationScenario(db.Model):
    __tablename__ = 'rationalization_scenarios'
    
    id = db.Column(db.Integer, primary_key=True)
    scenario_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    capability = db.Column(db.String(255), nullable=False)
    
    # Before state
    before_app_count = db.Column(db.Integer)
    before_integration_points = db.Column(db.Integer)
    before_db_technologies = db.Column(db.Integer)
    before_dev_teams = db.Column(db.Integer)
    before_cost = db.Column(db.Float)
    before_footprint = db.Column(db.Float)
    before_cyber_risk = db.Column(db.String(50))
    
    # After state
    after_app_count = db.Column(db.Integer)
    after_integration_points = db.Column(db.Integer)
    after_db_technologies = db.Column(db.Integer)
    after_dev_teams = db.Column(db.Integer)
    after_cost = db.Column(db.Float)
    after_footprint = db.Column(db.Float)
    after_cyber_risk = db.Column(db.String(50))
    
    # Metrics
    maintenance_reduction = db.Column(db.Float)  # Annual reduction in cost
    footprint_reduction_percent = db.Column(db.Float)  # Percentage reduction
    integration_complexity_reduction = db.Column(db.Float)  # Percentage reduction
    cyber_risk_reduction = db.Column(db.Float)  # Percentage reduction
    
    target_erp = db.Column(db.String(100))  # SAP, Oracle, etc.
    timeline_months = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'scenario_name': self.scenario_name,
            'description': self.description,
            'capability': self.capability,
            'before': {
                'app_count': self.before_app_count,
                'integration_points': self.before_integration_points,
                'db_technologies': self.before_db_technologies,
                'dev_teams': self.before_dev_teams,
                'cost': self.before_cost,
                'footprint': self.before_footprint,
                'cyber_risk': self.before_cyber_risk,
            },
            'after': {
                'app_count': self.after_app_count,
                'integration_points': self.after_integration_points,
                'db_technologies': self.after_db_technologies,
                'dev_teams': self.after_dev_teams,
                'cost': self.after_cost,
                'footprint': self.after_footprint,
                'cyber_risk': self.after_cyber_risk,
            },
            'metrics': {
                'maintenance_reduction': self.maintenance_reduction,
                'footprint_reduction_percent': self.footprint_reduction_percent,
                'integration_complexity_reduction': self.integration_complexity_reduction,
                'cyber_risk_reduction': self.cyber_risk_reduction,
            },
            'target_erp': self.target_erp,
            'timeline_months': self.timeline_months,
            'created_at': self.created_at.isoformat(),
        }
