"""Industry Templates Data Models - Application data from Industry Templates"""

from app import db
from datetime import datetime


class IndustryTemplate(db.Model):
    """Parent table for Industry Template file metadata"""
    __tablename__ = 'industry_template_metadata'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(36), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    record_count = db.Column(db.Integer, default=0)
    
    # Relationships
    industry_data = db.relationship('IndustryData', backref='industry_template', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'file_id': self.file_id,
            'filename': self.filename,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'record_count': self.record_count,
        }


class IndustryData(db.Model):
    """Industry Templates Data Table"""
    __tablename__ = 'industry_data'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('industry_template_metadata.id'), nullable=False)
    app_id = db.Column(db.String(255), nullable=False, index=True)
    app_name = db.Column(db.String(500), nullable=False)
    business_owner = db.Column(db.String(255))
    architecture_type = db.Column(db.String(255))
    platform_host = db.Column(db.String(255))
    application_type = db.Column(db.String(255))
    install_type = db.Column(db.String(255))
    capabilities = db.Column(db.Text)  # Comma-separated or JSON formatted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'template_id': self.template_id,
            'app_id': self.app_id,
            'app_name': self.app_name,
            'business_owner': self.business_owner,
            'architecture_type': self.architecture_type,
            'platform_host': self.platform_host,
            'application_type': self.application_type,
            'install_type': self.install_type,
            'capabilities': self.capabilities,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
