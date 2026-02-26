from app import db
from datetime import datetime
import json

server_application = db.Table(
    'server_application',
    db.Column('server_id', db.Integer, db.ForeignKey('servers.id'), primary_key=True),
    db.Column('application_id', db.Integer, db.ForeignKey('applications.id'), primary_key=True)
)

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(255), nullable=False, unique=True)
    environment = db.Column(db.String(50))  # prd, dev, staging
    technology_stack = db.Column(db.Text)  # JSON array
    version = db.Column(db.String(100))
    deployment_path = db.Column(db.String(500))
    server_install_directory = db.Column(db.String(500))
    status = db.Column(db.String(50), default='Active')  # Active, Deprecated, Planned
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    repository_id = db.Column(db.Integer, db.ForeignKey('code_repositories.id'))
    
    dependencies = db.relationship(
        'ApplicationDependency',
        foreign_keys='ApplicationDependency.source_app_id',
        backref='source_app',
        lazy=True,
        cascade='all, delete-orphan'
    )
    
    def to_dict(self):
        techs = []
        if self.technology_stack:
            try:
                techs = json.loads(self.technology_stack)
            except:
                techs = []
        
        return {
            'id': self.id,
            'app_name': self.app_name,
            'environment': self.environment,
            'technology_stack': techs,
            'version': self.version,
            'deployment_path': self.deployment_path,
            'server_install_directory': self.server_install_directory,
            'status': self.status,
            'description': self.description,
            'repository_id': self.repository_id,
            'created_at': self.created_at.isoformat(),
        }

class ApplicationDependency(db.Model):
    __tablename__ = 'application_dependencies'
    
    id = db.Column(db.Integer, primary_key=True)
    source_app_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    target_app_name = db.Column(db.String(255), nullable=False)
    dependency_type = db.Column(db.String(100))  # API, Database, Cache, etc.
    criticality = db.Column(db.String(50))  # Critical, High, Medium, Low
    
    def to_dict(self):
        return {
            'id': self.id,
            'source_app_id': self.source_app_id,
            'target_app_name': self.target_app_name,
            'dependency_type': self.dependency_type,
            'criticality': self.criticality,
        }
