from app import db
from datetime import datetime

class BusinessCapability(db.Model):
    __tablename__ = 'business_capabilities'
    
    id = db.Column(db.Integer, primary_key=True)
    capability_name = db.Column(db.String(255), nullable=False, unique=True)
    parent_capability = db.Column(db.String(255))  # For hierarchical structure (L1, L2)
    description = db.Column(db.Text)
    
    mappings = db.relationship('CapabilityMapping', backref='capability', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'capability_name': self.capability_name,
            'parent_capability': self.parent_capability,
            'description': self.description,
            'mappings': [m.to_dict() for m in self.mappings],
        }

class CapabilityMapping(db.Model):
    __tablename__ = 'capability_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    capability_id = db.Column(db.Integer, db.ForeignKey('business_capabilities.id'), nullable=False)
    application_name = db.Column(db.String(255), nullable=False)
    technology = db.Column(db.String(100))
    erp_overlap = db.Column(db.String(100))  # None, Partial, Duplicate, Core ERP
    redundancy_level = db.Column(db.String(50))  # None, Low, Medium, High
    criticality = db.Column(db.String(50))  # Critical, High, Medium, Low
    owner_team = db.Column(db.String(255))
    maintenance_cost = db.Column(db.Float)  # Annual cost in currency units
    
    def to_dict(self):
        return {
            'id': self.id,
            'capability_id': self.capability_id,
            'application_name': self.application_name,
            'technology': self.technology,
            'erp_overlap': self.erp_overlap,
            'redundancy_level': self.redundancy_level,
            'criticality': self.criticality,
            'owner_team': self.owner_team,
            'maintenance_cost': self.maintenance_cost,
        }

class CapabilityApplication(db.Model):
    __tablename__ = 'capability_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    capability_name = db.Column(db.String(255), nullable=False)
    application_name = db.Column(db.String(255), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'capability_name': self.capability_name,
            'application_name': self.application_name,
        }
