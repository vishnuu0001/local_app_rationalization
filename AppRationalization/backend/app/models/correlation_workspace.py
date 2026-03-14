"""
CorrelationWorkspace schema
===========================
Stores a clean, enriched copy of all three source files
(CASTReport, CORENTReport, Business_Templates) together with
column-level traceability for every AI-predicted or copied value.

Tables
------
workspace_run          — one row per "Correlate" button click (audit trail)
workspace_cast_row     — one enriched CAST row per run
workspace_corent_row   — one enriched CORENT row per run
workspace_biz_row      — one enriched Business-Template row per run
workspace_column_update — one row per (run, file, column) that was AI-updated
workspace_correlation   — final correlation result rows linking all three sources
"""

from datetime import datetime
import json
from app import db


# ──────────────────────────────────────────────────────────────────────────
# Run metadata
# ──────────────────────────────────────────────────────────────────────────

class WorkspaceRun(db.Model):
    """Audit record for each correlation run."""
    __tablename__ = "workspace_runs"

    id           = db.Column(db.Integer, primary_key=True)
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    status       = db.Column(db.String(30), default="running")   # running|done|failed
    cast_rows        = db.Column(db.Integer, default=0)
    corent_rows      = db.Column(db.Integer, default=0)
    biz_rows         = db.Column(db.Integer, default=0)
    cast_predicted   = db.Column(db.Integer, default=0)   # cells AI-filled
    corent_predicted = db.Column(db.Integer, default=0)
    biz_predicted    = db.Column(db.Integer, default=0)
    matched_count    = db.Column(db.Integer, default=0)
    match_pct        = db.Column(db.Float,   default=0.0)
    llm_model        = db.Column(db.String(100), nullable=True)
    error_detail     = db.Column(db.Text, nullable=True)
    finished_at      = db.Column(db.DateTime, nullable=True)
    # SHA-1 of source Excel files (size+mtime) — used for skip-if-unchanged optimisation
    source_files_hash = db.Column(db.String(64), nullable=True)

    def to_dict(self):
        return {k: (v.isoformat() if isinstance(v, datetime) else v)
                for k, v in self.__dict__.items() if not k.startswith("_")}


# ──────────────────────────────────────────────────────────────────────────
# CAST rows
# ──────────────────────────────────────────────────────────────────────────

class WorkspaceCastRow(db.Model):
    """One enriched row from CASTReport per workspace run."""
    __tablename__ = "workspace_cast_rows"

    id     = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("workspace_runs.id"), nullable=False, index=True)

    # Identity
    app_id   = db.Column(db.String(255), nullable=True, index=True)
    app_name = db.Column(db.String(500), nullable=True)

    # CAST-specific columns (matches CASTReport.xlsx → Applications sheet)
    server_name                           = db.Column(db.String(500), nullable=True)
    repo_name                             = db.Column(db.String(500), nullable=True)
    application_architecture              = db.Column(db.String(255), nullable=True)
    source_code_availability              = db.Column(db.String(255), nullable=True)
    programming_language                  = db.Column(db.String(255), nullable=True)
    component_coupling                    = db.Column(db.String(255), nullable=True)
    cloud_suitability                     = db.Column(db.String(255), nullable=True)
    volume_external_dependencies          = db.Column(db.String(255), nullable=True)
    app_service_api_readiness             = db.Column(db.String(255), nullable=True)
    degree_of_code_protocols              = db.Column(db.String(255), nullable=True)
    code_design                           = db.Column(db.String(255), nullable=True)
    app_code_complexity_volume            = db.Column(db.String(255), nullable=True)
    distributed_architecture_design       = db.Column(db.String(255), nullable=True)
    application_type                      = db.Column(db.String(255), nullable=True)

    # Traceability
    ai_predicted_columns = db.Column(db.JSON, default=list)   # list[str]
    ai_confidence        = db.Column(db.JSON, default=dict)   # {col: float}
    source_row_index     = db.Column(db.Integer, nullable=True)
    # 'Yes' if any column was AI-predicted and written back to DB, 'No' otherwise
    last_updated         = db.Column(db.String(3), default='No', nullable=False)
    # Summary of AI-filled columns: {"app_id": "...", "updated_columns": ["col1", ...]}
    updated_rows         = db.Column(db.JSON, nullable=True)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


# ──────────────────────────────────────────────────────────────────────────
# CORENT rows
# ──────────────────────────────────────────────────────────────────────────

class WorkspaceCorentRow(db.Model):
    """One enriched row from CORENTReport per workspace run."""
    __tablename__ = "workspace_corent_rows"

    id     = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("workspace_runs.id"), nullable=False, index=True)

    # Identity — populated via correlation with CAST / Business data
    app_id      = db.Column(db.String(255), nullable=True, index=True)
    app_name    = db.Column(db.String(500), nullable=True)

    # CORENT server identity (natural key)
    server_ip   = db.Column(db.String(100), nullable=True, index=True)
    server_name = db.Column(db.String(500), nullable=True, index=True)

    # CORENT columns (matches CORENTReport.xlsx → CORENT sheet)
    architecture_type                     = db.Column(db.String(255), nullable=True)
    business_owner                        = db.Column(db.String(255), nullable=True)
    platform_host                         = db.Column(db.String(255), nullable=True)
    server_type                           = db.Column(db.String(255), nullable=True)
    operating_system                      = db.Column(db.String(255), nullable=True)
    cpu_core                              = db.Column(db.String(100), nullable=True)
    memory                                = db.Column(db.String(100), nullable=True)
    internal_storage                      = db.Column(db.String(100), nullable=True)
    external_storage                      = db.Column(db.String(100), nullable=True)
    storage_type                          = db.Column(db.String(100), nullable=True)
    db_storage                            = db.Column(db.String(100), nullable=True)
    db_engine                             = db.Column(db.String(255), nullable=True)
    environment                           = db.Column(db.String(100), nullable=True)
    install_type                          = db.Column(db.String(255), nullable=True)
    virtualization_attributes             = db.Column(db.String(255), nullable=True)
    compute_server_hardware_architecture  = db.Column(db.String(255), nullable=True)
    application_stability                 = db.Column(db.String(255), nullable=True)
    virtualization_state                  = db.Column(db.String(255), nullable=True)
    storage_decomposition                 = db.Column(db.String(255), nullable=True)
    flash_storage_used                    = db.Column(db.String(100), nullable=True)
    cpu_requirement                       = db.Column(db.String(255), nullable=True)
    memory_ram_requirement                = db.Column(db.String(255), nullable=True)
    mainframe_dependency                  = db.Column(db.String(255), nullable=True)
    desktop_dependency                    = db.Column(db.String(255), nullable=True)
    app_os_platform_cloud_suitability     = db.Column(db.String(255), nullable=True)
    database_cloud_readiness              = db.Column(db.String(255), nullable=True)
    integration_middleware_cloud_readiness= db.Column(db.String(255), nullable=True)
    application_hardware_dependency       = db.Column(db.String(255), nullable=True)
    app_cots_vs_non_cots                  = db.Column(db.String(255), nullable=True)
    cloud_suitability                     = db.Column(db.String(255), nullable=True)
    volume_external_dependencies          = db.Column(db.String(255), nullable=True)
    app_load_predictability_elasticity    = db.Column(db.String(255), nullable=True)
    financially_optimizable_hardware      = db.Column(db.String(255), nullable=True)
    distributed_architecture_design       = db.Column(db.String(255), nullable=True)
    latency_requirements                  = db.Column(db.String(255), nullable=True)
    ubiquitous_access_requirements        = db.Column(db.String(255), nullable=True)
    no_production_environments            = db.Column(db.String(100), nullable=True)
    no_non_production_environments        = db.Column(db.String(100), nullable=True)
    ha_dr_requirements                    = db.Column(db.String(255), nullable=True)
    rto_requirements                      = db.Column(db.String(255), nullable=True)
    rpo_requirements                      = db.Column(db.String(255), nullable=True)
    deployment_geography                  = db.Column(db.String(255), nullable=True)

    # Traceability
    ai_predicted_columns = db.Column(db.JSON, default=list)
    ai_confidence        = db.Column(db.JSON, default=dict)
    source_row_index     = db.Column(db.Integer, nullable=True)
    last_updated         = db.Column(db.String(3), default='No', nullable=False)
    # Summary of AI-filled columns: {"app_id": "...", "updated_columns": ["col1", ...]}
    updated_rows         = db.Column(db.JSON, nullable=True)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


# ──────────────────────────────────────────────────────────────────────────
# Business Template rows
# ──────────────────────────────────────────────────────────────────────────

class WorkspaceBizRow(db.Model):
    """One enriched row from Business_Templates per workspace run."""
    __tablename__ = "workspace_biz_rows"

    id     = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("workspace_runs.id"), nullable=False, index=True)

    # Identity
    app_id   = db.Column(db.String(255), nullable=True, index=True)
    app_name = db.Column(db.String(500), nullable=True)

    # Business Template columns
    business_owner    = db.Column(db.String(255), nullable=True)
    architecture_type = db.Column(db.String(255), nullable=True)
    platform_host     = db.Column(db.String(255), nullable=True)
    application_type  = db.Column(db.String(255), nullable=True)
    install_type      = db.Column(db.String(255), nullable=True)
    capabilities      = db.Column(db.Text,        nullable=True)

    # Traceability
    ai_predicted_columns = db.Column(db.JSON, default=list)
    ai_confidence        = db.Column(db.JSON, default=dict)
    source_row_index     = db.Column(db.Integer, nullable=True)
    last_updated         = db.Column(db.String(3), default='No', nullable=False)
    # Summary of AI-filled columns: {"app_id": "...", "updated_columns": ["col1", ...]}
    updated_rows         = db.Column(db.JSON, nullable=True)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


# ──────────────────────────────────────────────────────────────────────────
# Column-level update traceability
# ──────────────────────────────────────────────────────────────────────────

class WorkspaceColumnUpdate(db.Model):
    """
    One row per cell that was AI-predicted or patched during a workspace run.

    Captures:
      - which file/source (CAST | CORENT | Business)
      - which column name (as it appears in the Excel)
      - original value (before prediction)
      - predicted value
      - confidence score
      - LLM model used
    """
    __tablename__ = "workspace_column_updates"

    id         = db.Column(db.Integer, primary_key=True)
    run_id     = db.Column(db.Integer, db.ForeignKey("workspace_runs.id"), nullable=False, index=True)
    source     = db.Column(db.String(30),  nullable=False, index=True)   # CAST|CORENT|Business
    app_id     = db.Column(db.String(255), nullable=True,  index=True)   # None for CORENT rows
    row_index  = db.Column(db.Integer,     nullable=True)                 # Excel row number
    column_name     = db.Column(db.String(255), nullable=False, index=True)
    original_value  = db.Column(db.Text, nullable=True)
    predicted_value = db.Column(db.Text, nullable=True)
    confidence      = db.Column(db.Float, default=0.75)
    llm_model       = db.Column(db.String(100), nullable=True)
    predicted_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {k: (v.isoformat() if isinstance(v, datetime) else v)
                for k, v in self.__dict__.items() if not k.startswith("_")}


# ──────────────────────────────────────────────────────────────────────────
# Correlation result rows (three-way join)
# ──────────────────────────────────────────────────────────────────────────

class WorkspaceCorrelation(db.Model):
    """
    One correlated record per application linking CAST + CORENT + Business data.
    Populated after the three-way correlation analysis in a run.
    """
    __tablename__ = "workspace_correlations"

    id     = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("workspace_runs.id"), nullable=False, index=True)

    # Identity
    app_id   = db.Column(db.String(255), nullable=True, index=True)
    app_name = db.Column(db.String(500), nullable=True)

    # FKs back to source-row tables
    cast_row_id   = db.Column(db.Integer, db.ForeignKey("workspace_cast_rows.id"),   nullable=True)
    corent_row_id = db.Column(db.Integer, db.ForeignKey("workspace_corent_rows.id"), nullable=True)
    biz_row_id    = db.Column(db.Integer, db.ForeignKey("workspace_biz_rows.id"),    nullable=True)

    # Match metadata
    match_type       = db.Column(db.String(30),  nullable=True)   # direct|server_name|fuzzy|unmatched
    match_confidence = db.Column(db.Float, default=0.0)
    match_criteria   = db.Column(db.Text,  nullable=True)

    # Cross-source key columns (denormalised for quick querying)
    cast_server_name    = db.Column(db.String(500), nullable=True)
    corent_server_name  = db.Column(db.String(500), nullable=True)
    biz_platform_host   = db.Column(db.String(255), nullable=True)

    # Aggregated cloud suitability (most specific wins)
    cloud_suitability = db.Column(db.String(255), nullable=True)

    # LLM deep-analysis for this application
    llm_annotation             = db.Column(db.Text, nullable=True)
    llm_migration_phase        = db.Column(db.Integer, nullable=True)   # 1|2|3
    llm_modernization_priority = db.Column(db.Integer, nullable=True)   # 1=highest
    llm_risk_level             = db.Column(db.String(30), nullable=True)  # high|medium|low

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {k: (v.isoformat() if isinstance(v, datetime) else v)
                for k, v in self.__dict__.items() if not k.startswith("_")}
