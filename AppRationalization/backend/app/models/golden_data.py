from app import db
from datetime import datetime


class GoldenData(db.Model):
    __tablename__ = 'golden_data'

    id = db.Column(db.Integer, primary_key=True)

    # Identity
    app_id   = db.Column(db.String(255), nullable=False, unique=True, index=True)
    app_name = db.Column(db.String(500))

    # Infrastructure / Hardware
    server_type                         = db.Column(db.String(255))
    operating_system                    = db.Column(db.String(255))
    cpu_core                            = db.Column(db.String(100))
    memory                              = db.Column(db.String(100))
    internal_storage                    = db.Column(db.String(100))
    external_storage                    = db.Column(db.String(100))
    storage_type                        = db.Column(db.String(255))
    db_storage                          = db.Column(db.String(100))
    db_engine                           = db.Column(db.String(255))
    environment_install_type            = db.Column(db.String(255))   # "Environment (INSTALL TYPE)"
    virtualization_attributes           = db.Column(db.String(255))
    compute_server_hardware_architecture = db.Column(db.String(255))
    application_stability               = db.Column(db.String(255))
    virtualization_state                = db.Column(db.String(255))
    storage_decomposition               = db.Column(db.String(255))
    flash_storage_used                  = db.Column(db.String(100))
    cpu_requirement                     = db.Column(db.String(255))
    memory_ram_requirement              = db.Column(db.String(255))
    mainframe_dependency                = db.Column(db.String(255))
    desktop_dependency                  = db.Column(db.String(255))

    # Cloud / Platform Readiness
    app_os_platform_cloud_suitability       = db.Column(db.String(255))
    database_cloud_readiness                = db.Column(db.String(255))
    integration_middleware_cloud_readiness  = db.Column(db.String(255))

    # Application Attributes
    application_architecture            = db.Column(db.String(255))
    application_hardware_dependency     = db.Column(db.String(255))
    app_cots_vs_non_cots                = db.Column(db.String(255))

    # Code / CAST Attributes
    source_code_availability            = db.Column(db.String(255))
    programming_language                = db.Column(db.String(255))
    component_coupling                  = db.Column(db.String(255))
    app_service_api_readiness           = db.Column(db.String(255))
    app_load_predictability_elasticity  = db.Column(db.String(255))
    degree_of_code_protocols            = db.Column(db.String(255))
    code_design                         = db.Column(db.String(255))
    application_code_complexity_volume  = db.Column(db.String(255))
    financially_optimizable_hardware_usage = db.Column(db.String(255))
    latency_requirements                = db.Column(db.String(255))
    ubiquitous_access_requirements      = db.Column(db.String(255))

    # Environments & SLA
    no_of_production_environments       = db.Column(db.Integer)
    no_of_non_production_environments   = db.Column(db.Integer)
    ha_dr_requirements                  = db.Column(db.String(255))
    rto_requirements                    = db.Column(db.String(255))
    rpo_requirements                    = db.Column(db.String(255))
    deployment_geography                = db.Column(db.String(255))

    # CORENT+CAST combined fields
    cloud_suitability                           = db.Column(db.String(255))
    volume_external_dependencies                = db.Column(db.String(255))
    distributed_architecture_design             = db.Column(db.String(255))

    # Survey fields (user-entered, or preserved from a previous run)
    level_of_data_residency_compliance          = db.Column(db.String(255))
    data_classification                         = db.Column(db.String(255))
    app_regulatory_contractual_requirements     = db.Column(db.String(255))
    impact_due_to_data_loss                     = db.Column(db.String(255))
    financial_impact_due_to_unavailability      = db.Column(db.String(255))
    business_criticality                        = db.Column(db.String(255))
    customer_facing                             = db.Column(db.String(255))
    application_status_lifecycle_state          = db.Column(db.String(255))
    availability_requirements                   = db.Column(db.String(255))
    support_level                               = db.Column(db.String(255))
    business_function_readiness                 = db.Column(db.String(255))
    level_of_internal_governance                = db.Column(db.String(255))
    no_of_internal_users                        = db.Column(db.String(255))
    no_of_external_users                        = db.Column(db.String(255))
    estimated_app_growth                        = db.Column(db.String(255))
    impact_to_users                             = db.Column(db.String(255))

    # Traceability: list of 0-based Excel column indices that were AI-predicted
    ai_filled_cols                              = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ------------------------------------------------------------------
    def to_dict(self):
        return {
            'id':                                    self.id,
            'app_id':                                self.app_id,
            'app_name':                              self.app_name,
            'server_type':                           self.server_type,
            'operating_system':                      self.operating_system,
            'cpu_core':                              self.cpu_core,
            'memory':                                self.memory,
            'internal_storage':                      self.internal_storage,
            'external_storage':                      self.external_storage,
            'storage_type':                          self.storage_type,
            'db_storage':                            self.db_storage,
            'db_engine':                             self.db_engine,
            'environment_install_type':              self.environment_install_type,
            'virtualization_attributes':             self.virtualization_attributes,
            'compute_server_hardware_architecture':  self.compute_server_hardware_architecture,
            'application_stability':                 self.application_stability,
            'virtualization_state':                  self.virtualization_state,
            'storage_decomposition':                 self.storage_decomposition,
            'flash_storage_used':                    self.flash_storage_used,
            'cpu_requirement':                       self.cpu_requirement,
            'memory_ram_requirement':                self.memory_ram_requirement,
            'mainframe_dependency':                  self.mainframe_dependency,
            'desktop_dependency':                    self.desktop_dependency,
            'app_os_platform_cloud_suitability':     self.app_os_platform_cloud_suitability,
            'database_cloud_readiness':              self.database_cloud_readiness,
            'integration_middleware_cloud_readiness': self.integration_middleware_cloud_readiness,
            'application_architecture':              self.application_architecture,
            'application_hardware_dependency':       self.application_hardware_dependency,
            'app_cots_vs_non_cots':                  self.app_cots_vs_non_cots,
            'source_code_availability':              self.source_code_availability,
            'programming_language':                  self.programming_language,
            'component_coupling':                    self.component_coupling,
            'app_service_api_readiness':             self.app_service_api_readiness,
            'app_load_predictability_elasticity':    self.app_load_predictability_elasticity,
            'degree_of_code_protocols':              self.degree_of_code_protocols,
            'code_design':                           self.code_design,
            'application_code_complexity_volume':    self.application_code_complexity_volume,
            'financially_optimizable_hardware_usage': self.financially_optimizable_hardware_usage,
            'latency_requirements':                  self.latency_requirements,
            'ubiquitous_access_requirements':        self.ubiquitous_access_requirements,
            'no_of_production_environments':         self.no_of_production_environments,
            'no_of_non_production_environments':     self.no_of_non_production_environments,
            'ha_dr_requirements':                    self.ha_dr_requirements,
            'rto_requirements':                      self.rto_requirements,
            'rpo_requirements':                      self.rpo_requirements,
            'deployment_geography':                  self.deployment_geography,
            # CORENT+CAST combined
            'cloud_suitability':                     self.cloud_suitability,
            'volume_external_dependencies':          self.volume_external_dependencies,
            'distributed_architecture_design':       self.distributed_architecture_design,
            # Survey fields
            'level_of_data_residency_compliance':    self.level_of_data_residency_compliance,
            'data_classification':                   self.data_classification,
            'app_regulatory_contractual_requirements': self.app_regulatory_contractual_requirements,
            'impact_due_to_data_loss':               self.impact_due_to_data_loss,
            'financial_impact_due_to_unavailability': self.financial_impact_due_to_unavailability,
            'business_criticality':                  self.business_criticality,
            'customer_facing':                       self.customer_facing,
            'application_status_lifecycle_state':    self.application_status_lifecycle_state,
            'availability_requirements':             self.availability_requirements,
            'support_level':                         self.support_level,
            'business_function_readiness':           self.business_function_readiness,
            'level_of_internal_governance':          self.level_of_internal_governance,
            'no_of_internal_users':                  self.no_of_internal_users,
            'no_of_external_users':                  self.no_of_external_users,
            'estimated_app_growth':                  self.estimated_app_growth,
            'impact_to_users':                       self.impact_to_users,
            # Traceability
            'ai_filled_cols':                        self.ai_filled_cols,
            'created_at':  self.created_at.isoformat() if self.created_at else None,
            'updated_at':  self.updated_at.isoformat() if self.updated_at else None,
        }
