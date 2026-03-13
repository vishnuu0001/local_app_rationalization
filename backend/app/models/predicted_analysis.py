"""
PredictedFieldValue    — fine-grained traceability for every LLM-predicted field.
LLMCorrelationAnalysis — holistic deep portfolio analysis stored after enrichment.

DB Schema design goals
-----------------------
• PredictedFieldValue captures WHICH column of WHICH source category was blank,
  what was predicted, by which model, on which prediction run.
• LLMCorrelationAnalysis stores the full structured deep analysis produced after
  all blank values have been populated, including migration roadmap, technical
  debt summary and modernisation priorities.
"""

import json
from datetime import datetime

from app import db


class PredictedFieldValue(db.Model):
    """
    One row per column that was null/blank and filled by the LLM.

    Traceability columns
    --------------------
    source_category : 'CORENT' | 'CAST' | 'Industry' — which data source
    column_name     : which column was updated
    app_id          : cross-source application identifier (nullable for CORENT
                      server-level records that carry no app_id)
    """

    __tablename__ = "predicted_field_values"

    id = db.Column(db.Integer, primary_key=True)

    # ── Traceability ────────────────────────────────────────────────────
    app_id          = db.Column(db.String(100), nullable=True,  index=True)
    source_category = db.Column(db.String(50),  nullable=False, index=True)
    # 'CORENT' | 'CAST' | 'Industry'
    column_name     = db.Column(db.String(255), nullable=False, index=True)

    # ── Prediction payload ───────────────────────────────────────────────
    original_value   = db.Column(db.Text, nullable=True)   # NULL / blank before
    predicted_value  = db.Column(db.Text, nullable=True)   # LLM output
    confidence_score = db.Column(db.Float,  default=0.0)
    prediction_model = db.Column(db.String(100), nullable=True)
    prediction_method = db.Column(db.String(50),  default="llm")
    # 'llm' | 'pattern' | 'statistical'

    # ── Foreign keys ─────────────────────────────────────────────────────
    prediction_run_id = db.Column(
        db.Integer,
        db.ForeignKey("correlation_results.id"),
        nullable=True,
        index=True,
    )
    consolidated_app_id = db.Column(
        db.Integer,
        db.ForeignKey("consolidated_apps.id"),
        nullable=True,
        index=True,
    )

    predicted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "app_id": self.app_id,
            "source_category": self.source_category,
            "column_name": self.column_name,
            "original_value": self.original_value,
            "predicted_value": self.predicted_value,
            "confidence_score": self.confidence_score,
            "prediction_model": self.prediction_model,
            "prediction_method": self.prediction_method,
            "prediction_run_id": self.prediction_run_id,
            "consolidated_app_id": self.consolidated_app_id,
            "predicted_at": self.predicted_at.isoformat() if self.predicted_at else None,
        }


class LLMCorrelationAnalysis(db.Model):
    """
    Holistic deep portfolio analysis produced by the LLM after data enrichment.

    Extends the basic portfolio view with:
      • 3-phase migration roadmap
      • Technical debt summary across the portfolio
      • Modernisation priorities ranked by urgency
    """

    __tablename__ = "llm_correlation_analyses"

    id = db.Column(db.Integer, primary_key=True)
    correlation_result_id = db.Column(
        db.Integer,
        db.ForeignKey("correlation_results.id"),
        nullable=True,
        index=True,
    )

    model_used    = db.Column(db.String(100), nullable=True)
    analysis_type = db.Column(db.String(50),  default="deep")
    # 'deep' | 'portfolio' | 'risk'

    # ── Analysis content ─────────────────────────────────────────────────
    executive_summary        = db.Column(db.Text, nullable=True)
    cloud_readiness_insight  = db.Column(db.Text, nullable=True)
    risk_observations        = db.Column(db.JSON, nullable=True)   # list[str]
    recommendations          = db.Column(db.JSON, nullable=True)   # list[str]
    correlation_quality      = db.Column(db.Text, nullable=True)
    per_app_notes            = db.Column(db.JSON, nullable=True)   # {app_id: str}

    # ── Deep analysis (new) ──────────────────────────────────────────────
    migration_roadmap        = db.Column(db.JSON, nullable=True)
    # list[{phase:int, title:str, apps:list[str], rationale:str}]

    technical_debt_summary   = db.Column(db.Text, nullable=True)

    modernization_priorities = db.Column(db.JSON, nullable=True)
    # list[{app_id:str, rationale:str, priority:int}]

    full_analysis = db.Column(db.JSON, nullable=True)   # raw LLM JSON

    # ── Metadata ─────────────────────────────────────────────────────────
    total_apps_analyzed    = db.Column(db.Integer, default=0)
    total_predictions_used = db.Column(db.Integer, default=0)
    match_percentage       = db.Column(db.Float,   default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "correlation_result_id": self.correlation_result_id,
            "model_used": self.model_used,
            "analysis_type": self.analysis_type,
            # Storage fields (original names)
            "executive_summary": self.executive_summary,
            "cloud_readiness_insight": self.cloud_readiness_insight,
            # Aliases expected by the frontend LLMAnalysisPanel
            "available": True,
            "summary": self.executive_summary or "",
            "cloud_readiness": self.cloud_readiness_insight or "",
            "risk_observations": self.risk_observations or [],
            "recommendations": self.recommendations or [],
            "correlation_quality": self.correlation_quality or "",
            "per_app_notes": self._clean_per_app_notes(self.per_app_notes or {}),
            "migration_roadmap": self.migration_roadmap or [],
            "technical_debt_summary": self.technical_debt_summary or "",
            "modernization_priorities": self.modernization_priorities or [],
            "total_apps_analyzed": self.total_apps_analyzed,
            "total_predictions_used": self.total_predictions_used,
            "match_percentage": self.match_percentage,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def _clean_per_app_notes(notes: dict) -> dict:
        """
        The LLM sometimes generates {"app_id": "TECHM1234: note..."} using the
        literal placeholder key 'app_id' instead of the actual ID.
        Detect and expand those entries so the frontend receives correct keys.
        """
        import re
        cleaned = {}
        for key, value in notes.items():
            text = str(value).strip()
            if key.lower() in ('app_id', 'application_id', 'id'):
                # The note value likely starts with "TECHM1234: rest of note"
                # Extract real app_id from the beginning of the text
                m = re.match(r'^([A-Za-z0-9_\-\.]+):\s*(.*)', text, re.DOTALL)
                if m:
                    cleaned[m.group(1)] = m.group(2).strip()
                else:
                    cleaned[key] = text  # give up — keep as-is
            else:
                cleaned[key] = text
        return cleaned
