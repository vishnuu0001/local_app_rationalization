"""
ConsolidatedApp model
=====================
Stores one row per application-level match across the three data sources
(CORENT / CAST / Industry Template).

Composite key:  cast_app_id  +  industry_app_id
  • Both come from external source systems that use an "APP ID" field.
  • Either may be NULL when no match was found for that source.
  • The pair is guaranteed unique via a UniqueConstraint.

AI-tracking columns:
  • ai_predicted_columns  — JSON list of column names filled by the LLM
  • ai_prediction_confidence — JSON object {column: 0.0-1.0}
  • llm_annotation        — one-sentence LLM summary of the application
"""

import json
from datetime import datetime

from app import db


class ConsolidatedApp(db.Model):
    """Unified application record merging CORENT + CAST + Industry data."""

    __tablename__ = "consolidated_apps"

    # ------------------------------------------------------------------
    # Surrogate primary key (SQLAlchemy / SQLite friendly)
    # ------------------------------------------------------------------
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ------------------------------------------------------------------
    # Composite business key  (cast_app_id, industry_app_id)
    # ------------------------------------------------------------------
    cast_app_id = db.Column(db.String(100), nullable=True, index=True)
    industry_app_id = db.Column(db.String(100), nullable=True, index=True)

    # Optional back-link to CorentData (by row id — CorentData has no app_id)
    corent_id = db.Column(db.Integer, db.ForeignKey("corent_data.id"), nullable=True)

    # ------------------------------------------------------------------
    # Merged application identity
    # ------------------------------------------------------------------
    app_id = db.Column(db.String(100), nullable=True, index=True)   # unified cross-source key
    app_name = db.Column(db.String(500), nullable=True)

    # ------------------------------------------------------------------
    # Industry Template fields
    # ------------------------------------------------------------------
    industry_business_owner = db.Column(db.String(255))
    industry_architecture_type = db.Column(db.String(255))
    industry_platform_host = db.Column(db.String(255))
    industry_application_type = db.Column(db.String(255))
    industry_install_type = db.Column(db.String(255))
    industry_capabilities = db.Column(db.Text)

    # ------------------------------------------------------------------
    # CAST fields
    # ------------------------------------------------------------------
    cast_application_architecture = db.Column(db.String(255))
    cast_source_code_availability = db.Column(db.String(255))
    cast_programming_language = db.Column(db.String(255))
    cast_component_coupling = db.Column(db.String(255))
    cast_cloud_suitability = db.Column(db.String(255))
    cast_volume_external_dependencies = db.Column(db.String(255))
    cast_code_design = db.Column(db.String(255))
    cast_server_name = db.Column(db.String(500))

    # ------------------------------------------------------------------
    # CORENT fields
    # ------------------------------------------------------------------
    corent_architecture_type = db.Column(db.String(255))
    corent_business_owner = db.Column(db.String(255))
    corent_platform_host = db.Column(db.String(255))
    corent_server_type = db.Column(db.String(255))
    corent_server_ip = db.Column(db.String(100))
    corent_server_name = db.Column(db.String(255))
    corent_operating_system = db.Column(db.String(255))
    corent_cpu_core = db.Column(db.String(100))
    corent_memory = db.Column(db.String(100))
    corent_internal_storage = db.Column(db.String(100))
    corent_environment = db.Column(db.String(100))
    corent_install_type = db.Column(db.String(255))
    corent_cloud_suitability = db.Column(db.String(255))
    corent_ha_dr_requirements = db.Column(db.String(255))
    corent_deployment_geography = db.Column(db.String(255))
    corent_db_engine = db.Column(db.String(255))
    corent_application_stability = db.Column(db.String(255))
    corent_mainframe_dependency = db.Column(db.String(255))
    corent_desktop_dependency = db.Column(db.String(255))
    corent_app_cots_vs_non_cots = db.Column(db.String(255))
    corent_volume_external_dependencies = db.Column(db.String(255))
    corent_rto_requirements = db.Column(db.String(255))
    corent_rpo_requirements = db.Column(db.String(255))

    # ------------------------------------------------------------------
    # AI / LLM tracking columns
    # ------------------------------------------------------------------
    ai_predicted_columns = db.Column(db.JSON, nullable=True, default=list)
    """JSON list: names of columns whose value was predicted by the LLM."""

    ai_prediction_confidence = db.Column(db.JSON, nullable=True, default=dict)
    """JSON dict: {column_name: float confidence 0-1} for each LLM-predicted field."""

    llm_annotation = db.Column(db.Text, nullable=True)
    """One-sentence LLM summary of the application for executive reporting."""

    # Correlation match metadata
    correlation_confidence = db.Column(db.Float, default=0.0)
    correlation_match_type = db.Column(db.String(50))    # "direct" | "fuzzy" | "unmatched"
    correlation_criteria = db.Column(db.Text)

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ------------------------------------------------------------------
    # Composite unique constraint (business key)
    # ------------------------------------------------------------------
    __table_args__ = (
        db.UniqueConstraint(
            "cast_app_id", "industry_app_id",
            name="uq_consolidated_cast_industry",
        ),
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_ai_predicted_columns(self) -> list:
        if isinstance(self.ai_predicted_columns, list):
            return self.ai_predicted_columns
        if isinstance(self.ai_predicted_columns, str):
            try:
                return json.loads(self.ai_predicted_columns)
            except Exception:
                return []
        return []

    def get_ai_prediction_confidence(self) -> dict:
        if isinstance(self.ai_prediction_confidence, dict):
            return self.ai_prediction_confidence
        if isinstance(self.ai_prediction_confidence, str):
            try:
                return json.loads(self.ai_prediction_confidence)
            except Exception:
                return {}
        return {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cast_app_id": self.cast_app_id,
            "industry_app_id": self.industry_app_id,
            "corent_id": self.corent_id,
            "app_id": self.app_id,
            "app_name": self.app_name,
            # Industry
            "industry_business_owner": self.industry_business_owner,
            "industry_architecture_type": self.industry_architecture_type,
            "industry_platform_host": self.industry_platform_host,
            "industry_application_type": self.industry_application_type,
            "industry_install_type": self.industry_install_type,
            "industry_capabilities": self.industry_capabilities,
            # CAST
            "cast_application_architecture": self.cast_application_architecture,
            "cast_source_code_availability": self.cast_source_code_availability,
            "cast_programming_language": self.cast_programming_language,
            "cast_component_coupling": self.cast_component_coupling,
            "cast_cloud_suitability": self.cast_cloud_suitability,
            "cast_volume_external_dependencies": self.cast_volume_external_dependencies,
            "cast_code_design": self.cast_code_design,
            "cast_server_name": self.cast_server_name,
            # CORENT
            "corent_architecture_type": self.corent_architecture_type,
            "corent_business_owner": self.corent_business_owner,
            "corent_platform_host": self.corent_platform_host,
            "corent_server_type": self.corent_server_type,
            "corent_server_ip": self.corent_server_ip,
            "corent_server_name": self.corent_server_name,
            "corent_operating_system": self.corent_operating_system,
            "corent_cpu_core": self.corent_cpu_core,
            "corent_memory": self.corent_memory,
            "corent_internal_storage": self.corent_internal_storage,
            "corent_environment": self.corent_environment,
            "corent_install_type": self.corent_install_type,
            "corent_cloud_suitability": self.corent_cloud_suitability,
            "corent_ha_dr_requirements": self.corent_ha_dr_requirements,
            "corent_deployment_geography": self.corent_deployment_geography,
            "corent_db_engine": self.corent_db_engine,
            "corent_application_stability": self.corent_application_stability,
            "corent_mainframe_dependency": self.corent_mainframe_dependency,
            "corent_desktop_dependency": self.corent_desktop_dependency,
            "corent_app_cots_vs_non_cots": self.corent_app_cots_vs_non_cots,
            "corent_volume_external_dependencies": self.corent_volume_external_dependencies,
            "corent_rto_requirements": self.corent_rto_requirements,
            "corent_rpo_requirements": self.corent_rpo_requirements,
            # AI tracking
            "ai_predicted_columns": self.get_ai_predicted_columns(),
            "ai_prediction_confidence": self.get_ai_prediction_confidence(),
            "llm_annotation": self.llm_annotation,
            # Correlation
            "correlation_confidence": self.correlation_confidence,
            "correlation_match_type": self.correlation_match_type,
            "correlation_criteria": self.correlation_criteria,
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
