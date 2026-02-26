import json
import uuid
from app.models.analysis import RationalizationScenario
from app import db

class RationalizationService:
    """Service for creating and managing rationalization scenarios"""
    
    @staticmethod
    def create_scenario(scenario_name, description, capability,
                       before_state, after_state, metrics, target_erp, timeline_months):
        """Create a new rationalization scenario"""
        scenario = RationalizationScenario(
            scenario_name=scenario_name,
            description=description,
            capability=capability,
            before_app_count=before_state.get('app_count'),
            before_integration_points=before_state.get('integration_points'),
            before_db_technologies=before_state.get('db_technologies'),
            before_dev_teams=before_state.get('dev_teams'),
            before_cost=before_state.get('cost'),
            before_footprint=before_state.get('footprint'),
            before_cyber_risk=before_state.get('cyber_risk'),
            after_app_count=after_state.get('app_count'),
            after_integration_points=after_state.get('integration_points'),
            after_db_technologies=after_state.get('db_technologies'),
            after_dev_teams=after_state.get('dev_teams'),
            after_cost=after_state.get('cost'),
            after_footprint=after_state.get('footprint'),
            after_cyber_risk=after_state.get('cyber_risk'),
            maintenance_reduction=metrics.get('maintenance_reduction'),
            footprint_reduction_percent=metrics.get('footprint_reduction_percent'),
            integration_complexity_reduction=metrics.get('integration_complexity_reduction'),
            cyber_risk_reduction=metrics.get('cyber_risk_reduction'),
            target_erp=target_erp,
            timeline_months=timeline_months
        )
        
        db.session.add(scenario)
        db.session.commit()
        return scenario
    
    @staticmethod
    def get_scenario(scenario_id):
        """Get a specific scenario"""
        scenario = RationalizationScenario.query.get(scenario_id)
        return scenario.to_dict() if scenario else None
    
    @staticmethod
    def get_scenarios_by_capability(capability):
        """Get all scenarios for a capability"""
        scenarios = RationalizationScenario.query.filter_by(capability=capability).all()
        return [s.to_dict() for s in scenarios]
    
    @staticmethod
    def get_all_scenarios():
        """Get all rationalization scenarios"""
        scenarios = RationalizationScenario.query.all()
        return [s.to_dict() for s in scenarios]
    
    @staticmethod
    def initialize_default_scenarios():
        """Initialize default rationalization scenarios"""
        scenarios = [
            {
                'scenario_name': 'Inventory Management to SAP EWM',
                'description': 'Consolidate 4 inventory systems to SAP Enterprise Warehouse Management',
                'capability': 'Inventory Management',
                'before_state': {
                    'app_count': 4,
                    'integration_points': 11,
                    'db_technologies': 3,
                    'dev_teams': 5,
                    'cost': 2800000,
                    'footprint': 850,
                    'cyber_risk': 'High'
                },
                'after_state': {
                    'app_count': 1,
                    'integration_points': 4,
                    'db_technologies': 1,
                    'dev_teams': 2,
                    'cost': 1000000,
                    'footprint': 650,
                    'cyber_risk': 'Low'
                },
                'metrics': {
                    'maintenance_reduction': 1800000,
                    'footprint_reduction_percent': 23.5,
                    'integration_complexity_reduction': 64,
                    'cyber_risk_reduction': 40
                },
                'target_erp': 'SAP',
                'timeline_months': 18
            },
            {
                'scenario_name': 'Finance GL Consolidation',
                'description': 'Consolidate finance systems to SAP Finance',
                'capability': 'General Ledger',
                'before_state': {
                    'app_count': 3,
                    'integration_points': 8,
                    'db_technologies': 2,
                    'dev_teams': 3,
                    'cost': 1500000,
                    'footprint': 450,
                    'cyber_risk': 'Medium'
                },
                'after_state': {
                    'app_count': 1,
                    'integration_points': 3,
                    'db_technologies': 1,
                    'dev_teams': 1,
                    'cost': 700000,
                    'footprint': 350,
                    'cyber_risk': 'Low'
                },
                'metrics': {
                    'maintenance_reduction': 800000,
                    'footprint_reduction_percent': 22,
                    'integration_complexity_reduction': 62.5,
                    'cyber_risk_reduction': 35
                },
                'target_erp': 'SAP',
                'timeline_months': 12
            }
        ]
        
        for scenario_data in scenarios:
            existing = RationalizationScenario.query.filter_by(
                scenario_name=scenario_data['scenario_name']
            ).first()
            
            if not existing:
                RationalizationService.create_scenario(
                    scenario_data['scenario_name'],
                    scenario_data['description'],
                    scenario_data['capability'],
                    scenario_data['before_state'],
                    scenario_data['after_state'],
                    scenario_data['metrics'],
                    scenario_data['target_erp'],
                    scenario_data['timeline_months']
                )
