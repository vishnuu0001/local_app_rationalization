from app import db
import json
from datetime import datetime


class CorrelationResult(db.Model):
    """Model for storing correlation results between Corent and CAST data"""
    __tablename__ = 'correlation_results'
    
    id = db.Column(db.Integer, primary_key=True)
    correlation_data = db.Column(db.JSON, nullable=False)  # Full correlation payload
    master_matrix = db.Column(db.JSON, nullable=False)     # Master matrix as JSON
    matched_count = db.Column(db.Integer, default=0)       # Number of matched items
    total_count = db.Column(db.Integer, default=0)         # Total Corent items
    match_percentage = db.Column(db.Float, default=0.0)    # Percentage matched
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    matrix_entries = db.relationship('MasterMatrixEntry', backref='correlation_result', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'matched_count': self.matched_count,
            'total_count': self.total_count,
            'match_percentage': self.match_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'correlation_data': json.loads(self.correlation_data) if isinstance(self.correlation_data, str) else self.correlation_data,
            'master_matrix': json.loads(self.master_matrix) if isinstance(self.master_matrix, str) else self.master_matrix,
            'matrix_entries_count': len(self.matrix_entries)
        }


class MasterMatrixEntry(db.Model):
    """Model for individual master matrix entries"""
    __tablename__ = 'master_matrix_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    correlation_result_id = db.Column(db.Integer, db.ForeignKey('correlation_results.id'), nullable=False)
    
    # Master matrix columns (as per requirements)
    app_name = db.Column(db.String(255), nullable=False, index=True)    # Application name
    infra = db.Column(db.String(255), nullable=True)                    # Server/hostname from Corent
    server = db.Column(db.String(255), nullable=True)                   # Domain/environment from Corent
    installed_app = db.Column(db.String(255), nullable=True)            # Application name from Corent
    app_component = db.Column(db.String(255), nullable=True)            # Framework/language from CAST
    repo = db.Column(db.Text, nullable=True)                            # Repository from CAST
    confidence = db.Column(db.Float, default=0.0, index=True)           # Correlation confidence score
    
    # Additional data stored as JSON
    entry_data = db.Column(db.JSON, nullable=False)  # Full entry details
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'app_name': self.app_name,
            'infra': self.infra,
            'server': self.server,
            'installed_app': self.installed_app,
            'app_component': self.app_component,
            'repo': self.repo,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'entry_data': json.loads(self.entry_data) if isinstance(self.entry_data, str) else self.entry_data
        }
