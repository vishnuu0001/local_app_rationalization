"""
ConsolidatedDataService
=======================
Orchestrates the three-step pipeline that runs when the user clicks
"Correlate Files & Start Analysis":

  Step 1  — Merge records from CORENT, CAST, and Industry Template tables.
  Step 2  — Call OllamaService to predict / fill null values per source,
             track which columns were AI-populated.
  Step 3  — Persist the enriched, consolidated records to `consolidated_apps`.
  Step 4  — Ask the LLM for a holistic correlation + portfolio analysis.
"""

import logging
import traceback
import concurrent.futures
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

from app import db
from app.models.cast import CASTData
from app.models.corent_data import CorentData
from app.models.industry_data import IndustryData
from app.models.consolidated_app import ConsolidatedApp
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _model_to_dict_safe(obj) -> Dict[str, Any]:
    """Convert a SQLAlchemy model instance to a plain dict (public fields only)."""
    if obj is None:
        return {}
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return {
        k: v
        for k, v in obj.__dict__.items()
        if not k.startswith("_")
    }


def _get_null_ratio(record: Dict[str, Any]) -> float:
    """Return fraction of non-id/timestamp fields that are null."""
    skip = {"id", "created_at", "updated_at", "template_id", "cast_analysis_id"}
    values = [v for k, v in record.items() if k not in skip]
    if not values:
        return 0.0
    nulls = sum(1 for v in values if v is None or str(v).strip() == "")
    return nulls / len(values)


def _sample_non_null_records(
    items: List[Dict[str, Any]],
    null_fields: List[str],
    n: int = 3,
) -> List[Dict[str, Any]]:
    """Return up to *n* records that have values for the given null fields."""
    candidates = [
        r for r in items
        if any(r.get(f) for f in null_fields)
    ]
    return candidates[:n]


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class ConsolidatedDataService:
    """Build, enrich, and persist consolidated application records."""

    # ------------------------------------------------------------------
    # Step 1 — Load raw records from all three source tables
    # ------------------------------------------------------------------

    @staticmethod
    def load_source_data() -> Tuple[
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
    ]:
        """
        Load all records from CORENT, CAST, and Industry tables.

        Returns
        -------
        corent_records  : list of CorentData dicts
        cast_records    : list of CASTData dicts
        industry_records: list of IndustryData dicts
        """
        corent_records = [_model_to_dict_safe(r) for r in CorentData.query.all()]
        cast_records = [_model_to_dict_safe(r) for r in CASTData.query.all()]
        industry_records = [_model_to_dict_safe(r) for r in IndustryData.query.all()]

        logger.info(
            "Loaded source data — CORENT:%d  CAST:%d  Industry:%d",
            len(corent_records), len(cast_records), len(industry_records),
        )
        return corent_records, cast_records, industry_records

    # ------------------------------------------------------------------
    # Step 2 — Predict nulls via Ollama (per source)
    # ------------------------------------------------------------------

    @staticmethod
    def predict_nulls_for_source(
        records: List[Dict[str, Any]],
        source: str,
    ) -> List[Dict[str, Any]]:
        """
        Predict null/missing fields for *records* using the LLM batch API.

        Uses OllamaService.predict_missing_fields_batch() which processes
        *batch_size* records per LLM call instead of one call per record,
        reducing total round-trips from N to ceil(N / batch_size).

        Each enriched record gains three meta-keys:
          _ai_predicted : list[str]        — column names filled by the LLM
          _ai_confidence: dict[str, float] — per-column confidence scores
          _ai_model     : str | None       — model that generated predictions

        This method is thread-safe — it makes only HTTP calls (no DB access).
        """
        def _mark_no_prediction():
            for r in records:
                r["_ai_predicted"]  = []
                r["_ai_confidence"] = {}
                r["_ai_model"]      = None

        try:
            if not OllamaService.is_available():
                logger.warning(
                    "Ollama not available — skipping null prediction for %s", source
                )
                _mark_no_prediction()
                return records

            model_used = OllamaService.get_selected_model()

            # Batch prediction: ceil(N / 16) LLM calls instead of N
            batch_results = OllamaService.predict_missing_fields_batch(
                records, source, batch_size=16
            )

            enriched: List[Dict[str, Any]] = []
            for record, (predictions, predicted_cols, confidence) in zip(records, batch_results):
                record.update(predictions)
                record["_ai_predicted"]  = predicted_cols
                record["_ai_confidence"] = confidence
                record["_ai_model"]      = model_used
                enriched.append(record)

            # Any records not covered by zip (shouldn't happen, but defensive)
            covered = len(enriched)
            if covered < len(records):
                for r in records[covered:]:
                    r["_ai_predicted"] = []; r["_ai_confidence"] = {}; r["_ai_model"] = model_used
                enriched.extend(records[covered:])

            filled_total = sum(len(r.get("_ai_predicted", [])) for r in enriched)
            logger.info(
                "Null prediction [%s]: %d columns AI-filled across %d records",
                source, filled_total, len(enriched),
            )
            return enriched

        except Exception:
            logger.warning(
                "predict_nulls_for_source [%s] failed — returning records without enrichment:\n%s",
                source, traceback.format_exc(),
            )
            _mark_no_prediction()
            return records

    # ------------------------------------------------------------------
    # Step 3 — Build merged consolidated records
    # ------------------------------------------------------------------

    @staticmethod
    def build_consolidated_records(
        corent_records: List[Dict[str, Any]],
        cast_records: List[Dict[str, Any]],
        industry_records: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Merge the three enriched source record lists into consolidated dicts.

        Match strategy:
          1. Join CASTData + IndustryData on app_id (direct match).
          2. CorentData has no app_id → link by row-index (best-effort positional
             alignment) or skip if no row with matching index.
        """
        # Index by app_id
        cast_by_id: Dict[str, Dict] = {}
        for r in cast_records:
            aid = r.get("app_id")
            if aid:
                cast_by_id[aid] = r

        industry_by_id: Dict[str, Dict] = {}
        for r in industry_records:
            aid = r.get("app_id")
            if aid:
                industry_by_id[aid] = r

        # All unique app_ids across both sources
        all_app_ids = set(cast_by_id.keys()) | set(industry_by_id.keys())

        consolidated: List[Dict[str, Any]] = []

        # Index CorentData by server_name for multi-key lookup.
        # Priority: CAST.server_name → CorentData.server_name
        #           Industry.platform_host → CorentData.server_name (fallback)
        #           Positional row-index (last resort)
        corent_by_server_name: Dict[str, Dict] = {}
        for r in corent_records:
            sname = (r.get("server_name") or "").strip().lower()
            if sname:
                corent_by_server_name[sname] = r
        corent_indexed = {i: r for i, r in enumerate(corent_records)}

        for idx, app_id in enumerate(sorted(all_app_ids)):
            cast_r = cast_by_id.get(app_id, {})
            industry_r = industry_by_id.get(app_id, {})

            # Attempt 1: CAST.server_name ↔ CorentData.server_name
            cast_sname = (cast_r.get("server_name") or "").strip().lower()
            corent_r = corent_by_server_name.get(cast_sname, {}) if cast_sname else {}

            # Attempt 2: Industry.platform_host ↔ CorentData.server_name
            if not corent_r:
                ind_host = (industry_r.get("platform_host") or "").strip().lower()
                corent_r = corent_by_server_name.get(ind_host, {}) if ind_host else {}

            # Attempt 3: Positional fallback
            if not corent_r:
                corent_r = corent_indexed.get(idx, {})

            # Determine app_name: prefer Industry > CAST
            app_name = (
                industry_r.get("app_name")
                or cast_r.get("app_name")
                or app_id
            )

            # Collect AI-predicted columns and confidence from all sources
            ai_predicted: List[str] = []
            ai_confidence: Dict[str, float] = {}

            for prefix, source_r in [
                ("industry", industry_r),
                ("cast", cast_r),
                ("corent", corent_r),
            ]:
                for col in source_r.get("_ai_predicted", []):
                    namespaced_col = f"{prefix}_{col}" if not col.startswith(prefix) else col
                    ai_predicted.append(namespaced_col)
                for col, conf in source_r.get("_ai_confidence", {}).items():
                    namespaced_col = f"{prefix}_{col}" if not col.startswith(prefix) else col
                    ai_confidence[namespaced_col] = conf

            record = {
                "app_id": app_id,
                "cast_app_id": cast_r.get("app_id"),
                "industry_app_id": industry_r.get("app_id"),
                "corent_id": corent_r.get("id"),
                "app_name": app_name,
                # Industry fields
                "industry_business_owner": industry_r.get("business_owner"),
                "industry_architecture_type": industry_r.get("architecture_type"),
                "industry_platform_host": industry_r.get("platform_host"),
                "industry_application_type": industry_r.get("application_type"),
                "industry_install_type": industry_r.get("install_type"),
                "industry_capabilities": industry_r.get("capabilities"),
                # CAST fields
                "cast_application_architecture": cast_r.get("application_architecture"),
                "cast_source_code_availability": cast_r.get("source_code_availability"),
                "cast_programming_language": cast_r.get("programming_language"),
                "cast_component_coupling": cast_r.get("component_coupling"),
                "cast_cloud_suitability": cast_r.get("cloud_suitability"),
                "cast_volume_external_dependencies": cast_r.get("volume_external_dependencies"),
                "cast_code_design": cast_r.get("code_design"),
                "cast_server_name": cast_r.get("server_name"),
                # CORENT fields
                "corent_architecture_type": corent_r.get("architecture_type"),
                "corent_business_owner": corent_r.get("business_owner"),
                "corent_platform_host": corent_r.get("platform_host"),
                "corent_server_type": corent_r.get("server_type"),
                "corent_server_ip": corent_r.get("server_ip"),
                "corent_server_name": corent_r.get("server_name"),
                "corent_operating_system": corent_r.get("operating_system"),
                "corent_cpu_core": corent_r.get("cpu_core"),
                "corent_memory": corent_r.get("memory"),
                "corent_internal_storage": corent_r.get("internal_storage"),
                "corent_environment": corent_r.get("environment"),
                "corent_install_type": corent_r.get("install_type"),
                "corent_cloud_suitability": corent_r.get("cloud_suitability"),
                "corent_ha_dr_requirements": corent_r.get("ha_dr_requirements"),
                "corent_deployment_geography": corent_r.get("deployment_geography"),
                "corent_db_engine": corent_r.get("db_engine"),
                "corent_application_stability": corent_r.get("application_stability"),
                "corent_mainframe_dependency": corent_r.get("mainframe_dependency"),
                "corent_desktop_dependency": corent_r.get("desktop_dependency"),
                "corent_app_cots_vs_non_cots": corent_r.get("app_cots_vs_non_cots"),
                "corent_volume_external_dependencies": corent_r.get("volume_external_dependencies"),
                "corent_rto_requirements": corent_r.get("rto_requirements"),
                "corent_rpo_requirements": corent_r.get("rpo_requirements"),
                # AI tracking
                "ai_predicted_columns": ai_predicted,
                "ai_prediction_confidence": ai_confidence,
            }
            consolidated.append(record)

        logger.info("Built %d consolidated records from %d unique app IDs", len(consolidated), len(all_app_ids))
        return consolidated

    # ------------------------------------------------------------------
    # Step 4 — Persist to DB
    # ------------------------------------------------------------------

    @staticmethod
    def persist_consolidated(
        consolidated_records: List[Dict[str, Any]],
        correlation_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, int]:
        """
        Upsert consolidated records into `consolidated_apps` table.

        Uses the composite (cast_app_id, industry_app_id) business key:
          - If a row exists → update it.
          - Otherwise → insert new row.

        Returns (inserted_count, updated_count).
        """
        inserted = updated = 0

        # Build match metadata from correlation_data
        match_meta: Dict[str, Dict] = {}
        if correlation_data:
            for match in correlation_data.get("correlation_layer", []):
                aid = match.get("app_id", "")
                match_meta[aid] = {
                    "confidence": match.get("confidence", 0.0),
                    "match_type": match.get("match_type", "unknown"),
                    "criteria": " | ".join(match.get("matching_criteria", [])),
                }

        # Pre-load ALL existing ConsolidatedApp rows in ONE query — avoids N+1
        # (previously: one SELECT per consolidated record)
        existing_map: Dict[tuple, ConsolidatedApp] = {
            (r.cast_app_id, r.industry_app_id): r
            for r in ConsolidatedApp.query.all()
        }

        for rec in consolidated_records:
            cast_aid = rec.get("cast_app_id")
            ind_aid = rec.get("industry_app_id")

            existing = existing_map.get((cast_aid, ind_aid))

            m = match_meta.get(rec.get("app_id", ""), {})

            if existing:
                row = existing
                updated += 1
            else:
                row = ConsolidatedApp()
                db.session.add(row)
                inserted += 1

            # Common field mapping
            row.cast_app_id = cast_aid
            row.industry_app_id = ind_aid
            row.corent_id = rec.get("corent_id")
            row.app_id = rec.get("app_id")
            row.app_name = rec.get("app_name")
            # Industry
            row.industry_business_owner = rec.get("industry_business_owner")
            row.industry_architecture_type = rec.get("industry_architecture_type")
            row.industry_platform_host = rec.get("industry_platform_host")
            row.industry_application_type = rec.get("industry_application_type")
            row.industry_install_type = rec.get("industry_install_type")
            row.industry_capabilities = rec.get("industry_capabilities")
            # CAST
            row.cast_application_architecture = rec.get("cast_application_architecture")
            row.cast_source_code_availability = rec.get("cast_source_code_availability")
            row.cast_programming_language = rec.get("cast_programming_language")
            row.cast_component_coupling = rec.get("cast_component_coupling")
            row.cast_cloud_suitability = rec.get("cast_cloud_suitability")
            row.cast_volume_external_dependencies = rec.get("cast_volume_external_dependencies")
            row.cast_code_design = rec.get("cast_code_design")
            row.cast_server_name = rec.get("cast_server_name")
            # CORENT
            row.corent_architecture_type = rec.get("corent_architecture_type")
            row.corent_business_owner = rec.get("corent_business_owner")
            row.corent_platform_host = rec.get("corent_platform_host")
            row.corent_server_type = rec.get("corent_server_type")
            row.corent_server_ip = rec.get("corent_server_ip")
            row.corent_server_name = rec.get("corent_server_name")
            row.corent_operating_system = rec.get("corent_operating_system")
            row.corent_cpu_core = rec.get("corent_cpu_core")
            row.corent_memory = rec.get("corent_memory")
            row.corent_internal_storage = rec.get("corent_internal_storage")
            row.corent_environment = rec.get("corent_environment")
            row.corent_install_type = rec.get("corent_install_type")
            row.corent_cloud_suitability = rec.get("corent_cloud_suitability")
            row.corent_ha_dr_requirements = rec.get("corent_ha_dr_requirements")
            row.corent_deployment_geography = rec.get("corent_deployment_geography")
            row.corent_db_engine = rec.get("corent_db_engine")
            row.corent_application_stability = rec.get("corent_application_stability")
            row.corent_mainframe_dependency = rec.get("corent_mainframe_dependency")
            row.corent_desktop_dependency = rec.get("corent_desktop_dependency")
            row.corent_app_cots_vs_non_cots = rec.get("corent_app_cots_vs_non_cots")
            row.corent_volume_external_dependencies = rec.get("corent_volume_external_dependencies")
            row.corent_rto_requirements = rec.get("corent_rto_requirements")
            row.corent_rpo_requirements = rec.get("corent_rpo_requirements")
            # AI tracking
            row.ai_predicted_columns = rec.get("ai_predicted_columns", [])
            row.ai_prediction_confidence = rec.get("ai_prediction_confidence", {})
            row.llm_annotation = rec.get("llm_annotation")
            # Correlation
            row.correlation_confidence = m.get("confidence", 0.0)
            row.correlation_match_type = m.get("match_type")
            row.correlation_criteria = m.get("criteria")

        db.session.commit()
        logger.info(
            "Persisted consolidated apps: %d inserted, %d updated", inserted, updated
        )
        return inserted, updated

    # ------------------------------------------------------------------
    # Convenience: full pipeline
    # ------------------------------------------------------------------

    @classmethod
    def run_full_pipeline(
        cls,
        correlation_data: Optional[Dict[str, Any]] = None,
        correlation_result_id: Optional[int] = None,
        run_llm_annotation: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute the complete null-prediction + consolidation + deep-analysis pipeline.

        Steps
        -----
        1. Load raw records from CORENT, CAST, and Industry tables.
        2. Predict null/blank fields concurrently across all three sources
           (each source runs in its own thread; each source uses LLM batching).
        3. Merge into consolidated records.
        4. Persist consolidated apps to DB.
        5. Save PredictedFieldValue traceability rows (bulk insert).
        6. Run deep LLM correlation analysis and persist to LLMCorrelationAnalysis.

        Parameters
        ----------
        correlation_data       : output of CorrelationService.correlate_data()
        correlation_result_id  : PK of the just-created CorrelationResult row
        run_llm_annotation     : if True, generate a per-app one-line annotation (slow)
        """
        from app.models.predicted_analysis import LLMCorrelationAnalysis  # lazy import
        from app.models.consolidated_app import ConsolidatedApp

        # ── Step 1: Load ───────────────────────────────────────────────────────
        corent_records, cast_records, industry_records = cls.load_source_data()

        ollama_available = OllamaService.is_available()

        # ── Step 2: Skip null prediction — ExcelPredictionService already ran LLM
        # prediction and wrote enriched values back to the Excel/DB. The DB records
        # loaded above therefore have no remaining nulls. Mark them as pre-enriched
        # rather than running a second identical LLM pass (which was the main cause
        # of the 10-minute stall).
        for r in corent_records + cast_records + industry_records:
            r.setdefault("_ai_predicted", [])
            r.setdefault("_ai_confidence", {})
            r.setdefault("_ai_model", OllamaService.get_selected_model() if ollama_available else None)

        # ── Step 3: Merge ───────────────────────────────────────────────────────
        consolidated = cls.build_consolidated_records(
            corent_records, cast_records, industry_records
        )

        # Optional per-app LLM annotation
        if ollama_available and run_llm_annotation:
            for rec in consolidated:
                rec["llm_annotation"] = OllamaService.annotate_application(rec)
        else:
            for rec in consolidated:
                rec["llm_annotation"] = None

        # ── Step 4: Persist consolidated apps ──────────────────────────────────
        inserted, updated = cls.persist_consolidated(consolidated, correlation_data)

        # ── Step 5: Save PredictedFieldValue traceability rows ─────────────────
        total_predictions = 0
        if ollama_available and correlation_result_id is not None:
            # Build app_id → consolidated_apps.id in a single query (no N+1)
            app_id_list = [r.get("app_id") for r in consolidated if r.get("app_id")]
            cons_id_map: Dict[str, int] = {
                row.app_id: row.id
                for row in ConsolidatedApp.query.filter(
                    ConsolidatedApp.app_id.in_(app_id_list)
                ).all()
            } if app_id_list else {}

            total_predictions += cls.save_predicted_field_values(
                cast_records, "CAST", correlation_result_id, cons_id_map
            )
            total_predictions += cls.save_predicted_field_values(
                industry_records, "Industry", correlation_result_id, cons_id_map
            )
            # CORENT records carry no app_id — saved with app_id=None for completeness
            total_predictions += cls.save_predicted_field_values(
                corent_records, "CORENT", correlation_result_id, cons_id_map
            )

        # ── Step 6: Deep LLM analysis + persist ────────────────────────────────
        stats: Dict[str, Any] = {
            "total_apps":           len(consolidated),
            "corent_source_rows":   len(corent_records),
            "cast_source_rows":     len(cast_records),
            "industry_source_rows": len(industry_records),
            "newly_inserted":       inserted,
            "updated_rows":         updated,
            "ollama_available":     ollama_available,
            "total_predictions":    total_predictions,
        }
        if correlation_data:
            stats.update(correlation_data.get("statistics", {}))

        predictions_summary: Dict[str, Any] = {
            "total_fields_predicted": total_predictions,
            "sources_enriched": ["CORENT", "CAST", "Industry"] if ollama_available else [],
            "model_used": OllamaService.get_selected_model() if ollama_available else None,
        }

        llm_analysis: Dict[str, Any] = {}
        llm_analysis_id: Optional[int] = None

        _LLM_ANALYSIS_TIMEOUT = 150  # hard wall-clock limit (seconds) — qwen2.5:14b on GPU needs ~90-120s for 195 apps

        if ollama_available:
            # Run in a background thread so we can impose a hard timeout.
            # If the LLM model is slow the pipeline still returns quickly.
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _ex:
                _future = _ex.submit(
                    OllamaService.generate_deep_correlation_analysis,
                    consolidated_records=consolidated,
                    statistics=stats,
                    predictions_summary=predictions_summary,
                )
                try:
                    llm_analysis = _future.result(timeout=_LLM_ANALYSIS_TIMEOUT)
                except concurrent.futures.TimeoutError:
                    _future.cancel()
                    logger.warning(
                        "generate_deep_correlation_analysis timed out after %ds — "
                        "returning correlation results without LLM analysis.",
                        _LLM_ANALYSIS_TIMEOUT,
                    )
                    llm_analysis = {
                        "available": False,
                        "summary": (
                            f"AI analysis timed out after {_LLM_ANALYSIS_TIMEOUT}s. "
                            "Correlation results are still complete. "
                            "Try again or use a faster Ollama model."
                        ),
                        "model_used": OllamaService.get_selected_model(),
                    }
                except Exception as _exc:
                    logger.warning("generate_deep_correlation_analysis failed: %s", _exc)
                    llm_analysis = {
                        "available": False,
                        "summary": f"AI analysis failed: {_exc}",
                        "model_used": OllamaService.get_selected_model(),
                    }

            # Persist to LLMCorrelationAnalysis table (only if we got a real result)
            if llm_analysis.get("available") and correlation_result_id is not None:
                analysis_row = LLMCorrelationAnalysis(
                    correlation_result_id    = correlation_result_id,
                    model_used               = llm_analysis.get("model_used"),
                    analysis_type            = "deep",
                    executive_summary        = llm_analysis.get("summary", ""),
                    cloud_readiness_insight  = llm_analysis.get("cloud_readiness", ""),
                    risk_observations        = llm_analysis.get("risk_observations", []),
                    recommendations          = llm_analysis.get("recommendations", []),
                    correlation_quality      = llm_analysis.get("correlation_quality", ""),
                    per_app_notes            = llm_analysis.get("per_app_notes", {}),
                    migration_roadmap        = llm_analysis.get("migration_roadmap", []),
                    technical_debt_summary   = llm_analysis.get("technical_debt_summary", ""),
                    modernization_priorities = llm_analysis.get("modernization_priorities", []),
                    full_analysis            = llm_analysis,
                    total_apps_analyzed      = len(consolidated),
                    total_predictions_used   = total_predictions,
                    match_percentage         = float(stats.get("match_percentage", 0.0)),
                )
                db.session.add(analysis_row)
                db.session.commit()
                llm_analysis_id = analysis_row.id
        else:
            llm_analysis = {
                "available": False,
                "summary": (
                    "Ollama LLM not reachable on localhost:11434. "
                    "Start Ollama and pull the model: `ollama pull mistral`"
                ),
            }

        total_ai_fills    = sum(len(r.get("ai_predicted_columns", [])) for r in consolidated)
        apps_with_ai_fill = sum(1 for r in consolidated if r.get("ai_predicted_columns"))

        return {
            "pipeline_stats": {
                **stats,
                "total_ai_fills":          total_ai_fills,
                "apps_with_ai_fill":        apps_with_ai_fill,
                "total_predictions_saved":  total_predictions,
            },
            "llm_analysis":      llm_analysis,
            "llm_analysis_id":   llm_analysis_id,
            "consolidated_count": len(consolidated),
        }

    # ------------------------------------------------------------------
    # Traceability: save per-field predictions to DB
    # ------------------------------------------------------------------

    @staticmethod
    def save_predicted_field_values(
        enriched_records: List[Dict[str, Any]],
        source_category: str,
        prediction_run_id: Optional[int],
        consolidated_app_id_map: Dict[str, int],
    ) -> int:
        """
        Bulk-save one PredictedFieldValue row per LLM-predicted column.

        Parameters
        ----------
        enriched_records       : records already processed by predict_nulls_for_source
        source_category        : 'CORENT' | 'CAST' | 'Industry'
        prediction_run_id      : FK to correlation_results.id (traceability)
        consolidated_app_id_map: {app_id → consolidated_apps.id}

        Returns total rows inserted.
        """
        from app.models.predicted_analysis import PredictedFieldValue  # lazy to avoid circular import

        rows = []
        for record in enriched_records:
            app_id         = record.get("app_id")
            predicted_cols = record.get("_ai_predicted", [])
            confidence_map = record.get("_ai_confidence", {})
            model_used     = record.get("_ai_model")

            for col in predicted_cols:
                rows.append(PredictedFieldValue(
                    app_id              = app_id,
                    source_category     = source_category,
                    column_name         = col,
                    original_value      = None,           # was null/blank
                    predicted_value     = str(record.get(col) or ""),
                    confidence_score    = confidence_map.get(col, 0.75),
                    prediction_model    = model_used,
                    prediction_method   = "llm",
                    prediction_run_id   = prediction_run_id,
                    consolidated_app_id = consolidated_app_id_map.get(app_id) if app_id else None,
                ))

        if rows:
            db.session.bulk_save_objects(rows)
            db.session.commit()
            logger.info(
                "Saved %d PredictedFieldValue rows for source: %s",
                len(rows), source_category,
            )
        return len(rows)

    # ------------------------------------------------------------------
    # Query helpers (used by routes)
    # ------------------------------------------------------------------

    @staticmethod
    def get_all_consolidated() -> List[Dict[str, Any]]:
        """Return all consolidated app records as dicts."""
        return [r.to_dict() for r in ConsolidatedApp.query.order_by(ConsolidatedApp.app_id).all()]

    @staticmethod
    def get_consolidated_stats() -> Dict[str, Any]:
        """Return aggregate stats on the consolidated table."""
        total = ConsolidatedApp.query.count()
        ai_predicted = ConsolidatedApp.query.filter(
            ConsolidatedApp.ai_predicted_columns != None,  # noqa: E711
            ConsolidatedApp.ai_predicted_columns != "[]",
        ).count()
        direct = ConsolidatedApp.query.filter_by(correlation_match_type="direct").count()
        fuzzy = ConsolidatedApp.query.filter_by(correlation_match_type="fuzzy").count()
        unmatched = ConsolidatedApp.query.filter_by(correlation_match_type="unmatched").count()

        return {
            "total_consolidated_apps": total,
            "apps_with_ai_predictions": ai_predicted,
            "apps_ai_prediction_pct": round(ai_predicted / max(total, 1) * 100, 1),
            "direct_matches": direct,
            "fuzzy_matches": fuzzy,
            "unmatched": unmatched,
        }
