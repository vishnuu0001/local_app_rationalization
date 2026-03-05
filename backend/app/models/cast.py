"""CAST Analysis Models - Application Inventory, Classification, and Architecture"""

from app import db
from datetime import datetime

class CASTAnalysis(db.Model):
    """Parent table for CAST report metadata"""
    __tablename__ = 'cast_analysis'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(36), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    extracted_at = db.Column(db.DateTime)
    
    # Relationships
    app_inventory = db.relationship('ApplicationInventory', backref='cast_analysis', cascade='all, delete-orphan')
    app_classifications = db.relationship('ApplicationClassification', backref='cast_analysis', cascade='all, delete-orphan')
    internal_architectures = db.relationship('InternalArchitecture', backref='cast_analysis', cascade='all, delete-orphan')
    high_risk_applications = db.relationship('HighRiskApplication', backref='cast_analysis', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'file_id': self.file_id,
            'filename': self.filename,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
        }


class ApplicationInventory(db.Model):
    """
    Application Inventory table from CAST Analysis
    Columns: APP ID, Application, Repo, Primary Language, Framework, LOC (K), 
    Modules, DB, Ext Int, Quality, Security, Cloud Ready
    """
    __tablename__ = 'cast_app_inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    cast_analysis_id = db.Column(db.Integer, db.ForeignKey('cast_analysis.id'), nullable=False)
    app_id = db.Column(db.String(50), nullable=False, index=True)  # Unique identifier
    application = db.Column(db.String(255), nullable=False)
    repo = db.Column(db.String(255))
    primary_language = db.Column(db.String(100))
    framework = db.Column(db.String(100))
    loc_k = db.Column(db.Float)  # Lines of Code in thousands
    modules = db.Column(db.Integer)  # Number of modules
    db_name = db.Column(db.String(255))  # Database
    ext_int = db.Column(db.String(255))  # External Integrations
    quality = db.Column(db.String(50))  # Quality rating
    security = db.Column(db.String(50))  # Security rating
    cloud_ready = db.Column(db.String(50))  # Cloud readiness
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('cast_analysis_id', 'app_id', name='uq_cast_app_inventory'),
    )
    
    def to_dict(self):
        return {
            'app_id': self.app_id,
            'application': self.application,
            'repo': self.repo,
            'primary_language': self.primary_language,
            'framework': self.framework,
            'loc_k': self.loc_k,
            'modules': self.modules,
            'db': self.db_name,
            'ext_int': self.ext_int,
            'quality': self.quality,
            'security': self.security,
            'cloud_ready': self.cloud_ready,
        }


class ApplicationClassification(db.Model):
    """
    Application Classification table from CAST Analysis
    Columns: APP ID, Application, Business owner, Application Type, Install Type, Capabilities
    """
    __tablename__ = 'cast_app_classification'
    
    id = db.Column(db.Integer, primary_key=True)
    cast_analysis_id = db.Column(db.Integer, db.ForeignKey('cast_analysis.id'), nullable=False)
    app_id = db.Column(db.String(50), nullable=False, index=True)
    application = db.Column(db.String(255), nullable=False)
    business_owner = db.Column(db.String(255))
    application_type = db.Column(db.String(100))  # Commercial, Custom, Open Source, etc.
    install_type = db.Column(db.String(100))  # Cloud, On Premise, Hybrid, etc.
    capabilities = db.Column(db.Text)  # Comma-separated or JSON array of capabilities
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('cast_analysis_id', 'app_id', name='uq_cast_app_classification'),
    )
    
    def to_dict(self):
        return {
            'app_id': self.app_id,
            'application': self.application,
            'business_owner': self.business_owner,
            'application_type': self.application_type,
            'install_type': self.install_type,
            'capabilities': self.capabilities,
        }


class InternalArchitecture(db.Model):
    """
    Internal Architecture table from CAST Analysis
    Columns: APP ID, Application, Module, Layer, Language, DB Calls, External Calls, App Type, Install Type
    """
    __tablename__ = 'cast_internal_architecture'
    
    id = db.Column(db.Integer, primary_key=True)
    cast_analysis_id = db.Column(db.Integer, db.ForeignKey('cast_analysis.id'), nullable=False)
    app_id = db.Column(db.String(50), nullable=False, index=True)
    application = db.Column(db.String(255), nullable=False)
    module = db.Column(db.String(255), nullable=False)
    layer = db.Column(db.String(100))  # Presentation, Business, Data, etc.
    language = db.Column(db.String(100))
    db_calls = db.Column(db.Integer)  # Number of database calls
    external_calls = db.Column(db.Integer)  # Number of external API/service calls
    app_type = db.Column(db.String(100))
    install_type = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'app_id': self.app_id,
            'application': self.application,
            'module': self.module,
            'layer': self.layer,
            'language': self.language,
            'db_calls': self.db_calls,
            'external_calls': self.external_calls,
            'app_type': self.app_type,
            'install_type': self.install_type,
        }


class HighRiskApplication(db.Model):
    """
    High-Risk Applications table from CAST Analysis
    Columns: Rank, APP ID, Application, Risk, Quality, Security, Cloud, App Type, Install Type, Capabilities
    """
    __tablename__ = 'cast_high_risk_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    cast_analysis_id = db.Column(db.Integer, db.ForeignKey('cast_analysis.id'), nullable=False)
    rank = db.Column(db.Integer, index=True)  # Risk ranking
    app_id = db.Column(db.String(50), nullable=False, index=True)
    application = db.Column(db.String(255), nullable=False)
    risk = db.Column(db.String(100))  # Risk level/score
    quality = db.Column(db.String(100))  # Quality rating
    security = db.Column(db.String(100))  # Security rating
    cloud = db.Column(db.String(100))  # Cloud readiness
    app_type = db.Column(db.String(100))
    install_type = db.Column(db.String(100))
    capabilities = db.Column(db.Text)  # Comma-separated list of capabilities
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'rank': self.rank,
            'app_id': self.app_id,
            'application': self.application,
            'risk': self.risk,
            'quality': self.quality,
            'security': self.security,
            'cloud': self.cloud,
            'app_type': self.app_type,
            'install_type': self.install_type,
            'capabilities': self.capabilities,
        }


class CASTData(db.Model):
    """
    CAST Analysis Data table - Detailed code analysis metrics and cloud readiness assessment
    """
    __tablename__ = 'cast_data'
    
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(255), nullable=False, unique=True)
    app_name = db.Column(db.String(500), nullable=False)
    repo_name = db.Column(db.String(500))
    application_architecture = db.Column(db.String(255))
    source_code_availability = db.Column(db.String(255))
    programming_language = db.Column(db.String(255))
    component_coupling = db.Column(db.String(255))
    cloud_suitability = db.Column(db.String(255))
    volume_external_dependencies = db.Column(db.String(255))
    app_service_api_readiness = db.Column(db.String(255))
    degree_of_code_protocols = db.Column(db.String(255))
    code_design = db.Column(db.String(255))
    application_code_complexity_volume = db.Column(db.String(255))
    distributed_architecture_design = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'app_id': self.app_id,
            'app_name': self.app_name,
            'repo_name': self.repo_name,
            'application_architecture': self.application_architecture,
            'source_code_availability': self.source_code_availability,
            'programming_language': self.programming_language,
            'component_coupling': self.component_coupling,
            'cloud_suitability': self.cloud_suitability,
            'volume_external_dependencies': self.volume_external_dependencies,
            'app_service_api_readiness': self.app_service_api_readiness,
            'degree_of_code_protocols': self.degree_of_code_protocols,
            'code_design': self.code_design,
            'application_code_complexity_volume': self.application_code_complexity_volume,
            'distributed_architecture_design': self.distributed_architecture_design,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

