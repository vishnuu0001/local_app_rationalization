import json
import uuid
from app.models.capability import BusinessCapability, CapabilityMapping, CapabilityApplication
from app.models.application import Application
from app.models.analysis import RationalizationScenario
from app import db

class CapabilityService:
    """Service for managing business capabilities and mappings"""
    
    @staticmethod
    def create_capability_mapping(capability_name, parent_capability=None, description=None):
        """Create a new business capability"""
        capability = BusinessCapability(
            capability_name=capability_name,
            parent_capability=parent_capability,
            description=description
        )
        db.session.add(capability)
        db.session.commit()
        return capability
    
    @staticmethod
    def map_application_to_capability(capability_id, app_name, technology, 
                                     erp_overlap, redundancy_level='None', 
                                     criticality='Medium', owner_team=None, 
                                     maintenance_cost=0.0):
        """Map an application to a capability"""
        mapping = CapabilityMapping(
            capability_id=capability_id,
            application_name=app_name,
            technology=technology,
            erp_overlap=erp_overlap,
            redundancy_level=redundancy_level,
            criticality=criticality,
            owner_team=owner_team,
            maintenance_cost=maintenance_cost
        )
        db.session.add(mapping)
        db.session.commit()
        return mapping
    
    @staticmethod
    def get_capability_with_applications(capability_id):
        """Get capability with all mapped applications"""
        capability = BusinessCapability.query.get(capability_id)
        if not capability:
            return None
        
        return {
            'id': capability.id,
            'capability_name': capability.capability_name,
            'parent_capability': capability.parent_capability,
            'description': capability.description,
            'mappings': [m.to_dict() for m in capability.mappings],
            'summary': {
                'total_applications': len(capability.mappings),
                'duplicate_count': sum(1 for m in capability.mappings if m.redundancy_level == 'High'),
                'total_maintenance_cost': sum(m.maintenance_cost or 0 for m in capability.mappings),
                'erp_coverage': {
                    'duplicate': len([m for m in capability.mappings if m.erp_overlap == 'Duplicate']),
                    'partial': len([m for m in capability.mappings if m.erp_overlap == 'Partial']),
                    'core': len([m for m in capability.mappings if m.erp_overlap == 'Core ERP']),
                    'none': len([m for m in capability.mappings if m.erp_overlap == 'None']),
                }
            }
        }
    
    @staticmethod
    def initialize_default_capabilities():
        """Initialize default business capabilities"""
        capabilities = [
            {
                'name': 'Production Execution',
                'parent': 'Manufacturing',
                'description': 'Manage manufacturing orders and production workflows'
            },
            {
                'name': 'Inventory Management',
                'parent': 'Manufacturing',
                'description': 'Track inventory across warehouses and locations'
            },
            {
                'name': 'General Ledger',
                'parent': 'Finance',
                'description': 'Core financial accounting and GL operations'
            },
            {
                'name': 'Accounts Payable',
                'parent': 'Finance',
                'description': 'Manage vendor payments and payables'
            },
            {
                'name': 'Supplier Management',
                'parent': 'Procurement',
                'description': 'Manage suppliers and supplier relationships'
            },
            {
                'name': 'Purchase Order Processing',
                'parent': 'Procurement',
                'description': 'Create and manage purchase orders'
            }
        ]
        
        for cap in capabilities:
            existing = BusinessCapability.query.filter_by(capability_name=cap['name']).first()
            if not existing:
                capability = CapabilityService.create_capability_mapping(
                    cap['name'],
                    cap['parent'],
                    cap['description']
                )
    
    @staticmethod
    def get_all_capabilities():
        """Get all business capabilities with mappings"""
        capabilities = BusinessCapability.query.all()
        return [CapabilityService.get_capability_with_applications(c.id) for c in capabilities]
