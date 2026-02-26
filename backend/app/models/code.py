from app import db
from datetime import datetime
import json

class CodeRepository(db.Model):
    __tablename__ = 'code_repositories'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(255), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    repo_url = db.Column(db.String(500), nullable=False)
    repo_name = db.Column(db.String(255), nullable=False)
    language = db.Column(db.String(100))
    framework = db.Column(db.String(100))
    primary_tech = db.Column(db.String(100))
    file_path = db.Column(db.String(500), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    components = db.relationship('ArchitectureComponent', backref='repository', lazy=True, cascade='all, delete-orphan')
    dependencies = db.relationship('InternalDependency', backref='repository', lazy=True, cascade='all, delete-orphan')
    
    applications = db.relationship('Application', backref='repository', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'file_id': self.file_id,
            'filename': self.filename,
            'repo_url': self.repo_url,
            'repo_name': self.repo_name,
            'language': self.language,
            'framework': self.framework,
            'primary_tech': self.primary_tech,
            'uploaded_at': self.uploaded_at.isoformat(),
            'components': [c.to_dict() for c in self.components],
            'dependencies': [d.to_dict() for d in self.dependencies],
        }

class ArchitectureComponent(db.Model):
    __tablename__ = 'architecture_components'
    
    id = db.Column(db.Integer, primary_key=True)
    repository_id = db.Column(db.Integer, db.ForeignKey('code_repositories.id'), nullable=False)
    component_name = db.Column(db.String(255), nullable=False)
    component_type = db.Column(db.String(100))  # Controller, Service, Repository, etc.
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    
    def to_dict(self):
        return {
            'id': self.id,
            'component_name': self.component_name,
            'component_type': self.component_type,
            'description': self.description,
            'file_path': self.file_path,
        }

class InternalDependency(db.Model):
    __tablename__ = 'internal_dependencies'
    
    id = db.Column(db.Integer, primary_key=True)
    repository_id = db.Column(db.Integer, db.ForeignKey('code_repositories.id'), nullable=False)
    source_component = db.Column(db.String(255), nullable=False)
    target_component = db.Column(db.String(255), nullable=False)
    dependency_type = db.Column(db.String(100))  # Imports, Calls, Extends, etc.
    external_api = db.Column(db.String(255))  # If it's external like ERP API
    
    def to_dict(self):
        return {
            'id': self.id,
            'source_component': self.source_component,
            'target_component': self.target_component,
            'dependency_type': self.dependency_type,
            'external_api': self.external_api,
        }
