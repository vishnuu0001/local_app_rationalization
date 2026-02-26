from app import db
from datetime import datetime
import json

class Infrastructure(db.Model):
    __tablename__ = 'infrastructure'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(255), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_vms = db.Column(db.Integer, default=0)
    total_k8s_clusters = db.Column(db.Integer, default=0)
    orphan_systems = db.Column(db.Integer, default=0)
    
    servers = db.relationship('Server', backref='infrastructure', lazy=True, cascade='all, delete-orphan')
    network_links = db.relationship('NetworkLink', backref='infrastructure', lazy=True, cascade='all, delete-orphan')
    infrastructure_discoveries = db.relationship('InfrastructureDiscovery', backref='infrastructure', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'file_id': self.file_id,
            'filename': self.filename,
            'uploaded_at': self.uploaded_at.isoformat(),
            'total_vms': self.total_vms,
            'total_k8s_clusters': self.total_k8s_clusters,
            'orphan_systems': self.orphan_systems,
            'servers': [s.to_dict() for s in self.servers],
        }

class Server(db.Model):
    __tablename__ = 'servers'
    
    id = db.Column(db.Integer, primary_key=True)
    infrastructure_id = db.Column(db.Integer, db.ForeignKey('infrastructure.id'), nullable=False)
    server_name = db.Column(db.String(255), nullable=False)
    environment = db.Column(db.String(50), nullable=False)  # prd, dev, staging, etc.
    server_type = db.Column(db.String(50), nullable=False)  # VM, Container, Physical
    ip_address = db.Column(db.String(50))
    deployment_footprint = db.Column(db.String(255))  # Cloud provider, datacenter
    installed_techs = db.Column(db.Text)  # JSON array of tech stack
    
    containers = db.relationship('Container', backref='server', lazy=True, cascade='all, delete-orphan')
    applications = db.relationship('Application', secondary='server_application', backref='servers')
    
    def to_dict(self):
        techs = []
        if self.installed_techs:
            try:
                techs = json.loads(self.installed_techs)
            except:
                techs = []
        
        return {
            'id': self.id,
            'server_name': self.server_name,
            'environment': self.environment,
            'server_type': self.server_type,
            'ip_address': self.ip_address,
            'deployment_footprint': self.deployment_footprint,
            'installed_techs': techs,
            'containers': [c.to_dict() for c in self.containers],
        }

class Container(db.Model):
    __tablename__ = 'containers'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'), nullable=False)
    container_id = db.Column(db.String(255))
    container_name = db.Column(db.String(255), nullable=False)
    image = db.Column(db.String(255))
    status = db.Column(db.String(50))  # running, stopped, etc.
    
    def to_dict(self):
        return {
            'id': self.id,
            'container_id': self.container_id,
            'container_name': self.container_name,
            'image': self.image,
            'status': self.status,
        }

class NetworkLink(db.Model):
    __tablename__ = 'network_links'
    
    id = db.Column(db.Integer, primary_key=True)
    infrastructure_id = db.Column(db.Integer, db.ForeignKey('infrastructure.id'), nullable=False)
    source_server = db.Column(db.String(255), nullable=False)
    target_server = db.Column(db.String(255), nullable=False)
    protocol = db.Column(db.String(50))
    port = db.Column(db.Integer)
    
    def to_dict(self):
        return {
            'id': self.id,
            'source_server': self.source_server,
            'target_server': self.target_server,
            'protocol': self.protocol,
            'port': self.port,
        }

class InfrastructureDiscovery(db.Model):
    """Infrastructure & Network Discovery table - discovered applications from CORENT PDF report"""
    __tablename__ = 'infrastructure_discovery'
    
    id = db.Column(db.Integer, primary_key=True)
    infrastructure_id = db.Column(db.Integer, db.ForeignKey('infrastructure.id'), nullable=False)
    
    # Table columns from Infrastructure & Network Discovery PDF (8 columns)
    app_id = db.Column(db.String(50), nullable=False, unique=True)  # APP ID
    name = db.Column(db.String(500), nullable=False)  # Name
    business_owner = db.Column(db.String(255))  # Business owner
    architecture_type = db.Column(db.String(255))  # Architecture type
    platform_host = db.Column(db.String(255))  # Platform Host
    application_type = db.Column(db.String(255))  # Application type
    install_type = db.Column(db.String(255))  # Install type
    capabilities = db.Column(db.Text)  # Capabilities
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'infrastructure_id': self.infrastructure_id,
            'app_id': self.app_id,
            'name': self.name,
            'business_owner': self.business_owner,
            'architecture_type': self.architecture_type,
            'platform_host': self.platform_host,
            'application_type': self.application_type,
            'install_type': self.install_type,
            'capabilities': self.capabilities,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

class BusinessCapabilities(db.Model):
    """Business Capabilities mapping from TestData_RussianOwners.xlsx"""
    __tablename__ = 'business_capabilties'
    
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(50), nullable=False, unique=True)  # APP ID
    name = db.Column(db.String(500), nullable=False)  # Name
    business_owner = db.Column(db.String(255))  # Business owner
    architecture_type = db.Column(db.String(255))  # Architecture type
    platform_host = db.Column(db.String(255))  # Platform Host
    application_type = db.Column(db.String(255))  # Application type
    install_type = db.Column(db.String(255))  # Install type
    capabilities = db.Column(db.Text)  # Capabilities (can be comma-separated or multi-line)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'app_id': self.app_id,
            'name': self.name,
            'business_owner': self.business_owner,
            'architecture_type': self.architecture_type,
            'platform_host': self.platform_host,
            'application_type': self.application_type,
            'install_type': self.install_type,
            'capabilities': self.capabilities,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }