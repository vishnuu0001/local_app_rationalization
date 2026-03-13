"""
ExcelPredictionService
======================
Orchestrates the "Correlate Files & Start Analysis" workspace pipeline:

1. Read source Excel files directly (backend/data/)
2. Load raw rows into workspace DB tables (last_updated = 'No')
3. Query DB rows with null fields → LLM batch-predict → UPDATE DB rows
   (last_updated = 'Yes' for any row where ≥1 field was AI-filled)
4. Correlate entirely from DB: CAST ↔ CORENT (APP ID / SERVER_NAME)
                                CAST ↔ Business (APP ID)
5. Store WorkspaceCorrelation records

All predicted values are persisted directly to the workspace DB tables.
No Excel copying or write-back is performed.
"""

import hashlib
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app import db
from app.models.correlation_workspace import (
    WorkspaceBizRow,
    WorkspaceCastRow,
    WorkspaceColumnUpdate,
    WorkspaceCorrelation,
    WorkspaceCorentRow,
    WorkspaceRun,
)
from app.services.ollama_service import OllamaService, apply_heuristic_fills

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants — computed relative to this file so they work regardless
# of the working-directory used at runtime (IIS, gunicorn, dev server …)
# ---------------------------------------------------------------------------
_BACKEND_DIR  = Path(__file__).resolve().parent.parent.parent          # backend/
_DATA_DIR     = _BACKEND_DIR / "data"

# Read directly from source — no UpdatedData copy needed
_CAST_SRC     = _DATA_DIR / "CASTReport.xlsx"
_CORENT_SRC   = _DATA_DIR / "CORENTReport.xlsx"
_BIZ_SRC      = _DATA_DIR / "Business_Templates.xlsx"

# Excel sheet names inside each file
_CAST_SHEET   = "Applications"
_CORENT_SHEET = "CORENT"
_BIZ_SHEET    = "Page 1"

# Column to model-field mappings
# (Excel column name → WorkspaceCastRow attribute name)
_CAST_COL_MAP: Dict[str, str] = {
    "APP ID":                                       "app_id",
    "APP NAME":                                     "app_name",
    "SERVER_NAME":                                  "server_name",
    "REPO_NAME":                                    "repo_name",
    "Application Architecture":                     "application_architecture",
    "Source Code Availability":                     "source_code_availability",
    "Programming Language":                         "programming_language",
    "Component Coupling":                           "component_coupling",
    "Cloud Suitability":                            "cloud_suitability",
    "Volume of External Dependencies":              "volume_external_dependencies",
    "App Service/API Readiness":                    "app_service_api_readiness",
    "Degree of Code Protocols":                     "degree_of_code_protocols",
    "Code Design":                                  "code_design",
    "Application-Code Complexity/Volume":           "app_code_complexity_volume",
    "Distributed Architecture Design or not":       "distributed_architecture_design",
    "Application Type":                             "application_type",
}

_CORENT_COL_MAP: Dict[str, str] = {
    "APP ID":                                       "app_id",
    "APP Name":                                     "app_name",
    "SERVER_IP":                                    "server_ip",
    "SERVER_NAME":                                  "server_name",
    "ArchitectureType":                             "architecture_type",
    "BusinessOwner":                                "business_owner",
    "PlatformHost":                                 "platform_host",
    "Server Type":                                  "server_type",
    "Operating System":                             "operating_system",
    "CPU Core":                                     "cpu_core",
    "Memory":                                       "memory",
    "Internal Storage":                             "internal_storage",
    "External Storage":                             "external_storage",
    "Storage Type":                                 "storage_type",
    "DB Storage":                                   "db_storage",
    "DB Engine":                                    "db_engine",
    "Environment":                                  "environment",
    "INSTALL TYPE":                                 "install_type",
    "Virtualization Attributes":                    "virtualization_attributes",
    "Compute/Server Hardware Architecture":         "compute_server_hardware_architecture",
    "Application Stability":                        "application_stability",
    "Virtualization State":                         "virtualization_state",
    "Storage Decomposition":                        "storage_decomposition",
    "FLASH Storage Used":                           "flash_storage_used",
    "CPU Requirement":                              "cpu_requirement",
    "Memory(RAM) Requirement":                      "memory_ram_requirement",
    "Mainframe Dependency":                         "mainframe_dependency",
    "Desktop Dependency":                           "desktop_dependency",
    "App OS/Platform Cloud Suitability":            "app_os_platform_cloud_suitability",
    "Database Cloud Readiness":                     "database_cloud_readiness",
    "Integration Middleware Cloud Readiness":       "integration_middleware_cloud_readiness",
    "Application Hardware dependency":              "application_hardware_dependency",
    "App COTS vs. Non-COTS Only":                   "app_cots_vs_non_cots",
    "Cloud Suitability":                            "cloud_suitability",
    "Volume of External Dependencies":              "volume_external_dependencies",
    "App Load Predictability/Elasticity":           "app_load_predictability_elasticity",
    "Financially Optimizable Hardware Usage":       "financially_optimizable_hardware",
    "Distributed Architecture Design or not":       "distributed_architecture_design",
    "Latency Requirements":                         "latency_requirements",
    "Ubiquitous Access Requirements":               "ubiquitous_access_requirements",
    "No. of Production Environments":               "no_production_environments",
    "No. of Non-Production Environments":           "no_non_production_environments",
    "HA/DR Requirements":                           "ha_dr_requirements",
    "RTO Requirements":                             "rto_requirements",
    "RPO Requirements":                             "rpo_requirements",
    "Deployment Geography":                         "deployment_geography",
}

_BIZ_COL_MAP: Dict[str, str] = {
    "APP ID":           "app_id",
    "APP Name":         "app_name",
    "Business owner":   "business_owner",
    "Architecture type":"architecture_type",
    "Platform Host":    "platform_host",
    "Application type": "application_type",
    "Install type":     "install_type",
    "Capabilities":     "capabilities",
}

# Map workspace source labels to Ollama schema prompts.
# Business_Templates should use the "industry" schema context in OllamaService.
_OLLAMA_SOURCE_MAP: Dict[str, str] = {
    "CAST": "cast",
    "CORENT": "corent",
    "Business": "industry",
}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _str_or_none(val: Any) -> Optional[str]:
    """Convert a DataFrame cell value to a clean string or None."""
    if val is None or (isinstance(val, float) and __import__("math").isnan(val)):
        return None
    s = str(val).strip()
    return s if s else None


def _row_to_dict(row: pd.Series, col_map: Dict[str, str]) -> Dict[str, Any]:
    """Map a DataFrame row to a flat dict using col_map (Excel col → field name)."""
    out: Dict[str, Any] = {}
    for excel_col, field_name in col_map.items():
        out[field_name] = _str_or_none(row.get(excel_col))
    return out


def _null_fields(d: Dict[str, Any]) -> List[str]:
    return [k for k, v in d.items() if v is None]


def _normalize_app_name(name: Optional[str]) -> str:
    """Lowercase, strip spaces and noise words for fuzzy app-name matching."""
    if not name:
        return ""
    n = name.lower().strip()
    for noise in (" application", " app", " system", " service", " platform", " module"):
        n = n.replace(noise, "")
    return n.replace(" ", "").replace("-", "").replace("_", "")


# ---------------------------------------------------------------------------
# Class
# ---------------------------------------------------------------------------

class ExcelPredictionService:
    """Orchestrates the DB-centric workspace pipeline (no Excel copy/write-back)."""

    # ------------------------------------------------------------------ #
    # Step 1 — Read source Excel files
    # ------------------------------------------------------------------ #

    @staticmethod
    def _compute_excel_hash() -> str:
        """
        Return a short SHA-1 fingerprint of the three source Excel files
        based on their file size and modification time.  Cheap to compute
        and stable enough for skip-if-unchanged detection.
        """
        h = hashlib.sha1()
        for path in (_CAST_SRC, _CORENT_SRC, _BIZ_SRC):
            try:
                st = path.stat()
                h.update(f"{path.name}:{st.st_size}:{st.st_mtime}".encode())
            except FileNotFoundError:
                h.update(f"{path.name}:missing".encode())
        return h.hexdigest()[:16]

    @staticmethod
    def _read_excel(path: Path, sheet: str) -> pd.DataFrame:
        try:
            df = pd.read_excel(str(path), sheet_name=sheet, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as exc:
            logger.error("Failed to read %s [%s]: %s", path, sheet, exc)
            return pd.DataFrame()

    # ------------------------------------------------------------------ #
    # Step 2 — Bulk-insert raw rows into workspace DB tables
    # ------------------------------------------------------------------ #

    @staticmethod
    def _load_cast_rows(df: pd.DataFrame, run_id: int) -> int:
        if df.empty:
            return 0
        rows = []
        for i, row in df.iterrows():
            rec = _row_to_dict(row, _CAST_COL_MAP)
            obj = WorkspaceCastRow(run_id=run_id, source_row_index=int(i), last_updated='No', **rec)
            rows.append(obj)
        db.session.bulk_save_objects(rows)
        db.session.flush()
        return len(rows)

    @staticmethod
    def _load_corent_rows(df: pd.DataFrame, run_id: int) -> int:
        if df.empty:
            return 0
        rows = []
        for i, row in df.iterrows():
            rec = _row_to_dict(row, _CORENT_COL_MAP)
            obj = WorkspaceCorentRow(run_id=run_id, source_row_index=int(i), last_updated='No', **rec)
            rows.append(obj)
        db.session.bulk_save_objects(rows)
        db.session.flush()
        return len(rows)

    @staticmethod
    def _load_biz_rows(df: pd.DataFrame, run_id: int) -> int:
        if df.empty:
            return 0
        rows = []
        for i, row in df.iterrows():
            rec = _row_to_dict(row, _BIZ_COL_MAP)
            obj = WorkspaceBizRow(run_id=run_id, source_row_index=int(i), last_updated='No', **rec)
            rows.append(obj)
        db.session.bulk_save_objects(rows)
        db.session.flush()
        return len(rows)

    # ------------------------------------------------------------------ #
    # Step 3 — LLM-predict null fields and UPDATE DB rows directly
    # ------------------------------------------------------------------ #

    @staticmethod
    def _predict_and_update_db(
        model_class: Any,
        run_id: int,
        field_names: List[str],
        source_label: str,
        app: Any,
    ) -> List[Dict[str, Any]]:
        """
        Query DB rows for *run_id*, batch-predict null fields via the LLM,
        write predicted values back to each row, and set last_updated='Yes'
        on rows where ≥1 field was AI-filled.

        Returns a flat list of WorkspaceColumnUpdate dicts.
        """
        updates: List[Dict[str, Any]] = []
        llm_source = _OLLAMA_SOURCE_MAP.get(source_label, source_label.lower())

        _skip = frozenset((
            "id", "run_id", "source_row_index", "last_updated",
            "ai_predicted_columns", "ai_confidence", "updated_rows",
            "created_at", "updated_at",
        ))

        with app.app_context():
            rows: List[Any] = model_class.query.filter_by(run_id=run_id).all()
            if not rows:
                return updates

            # Track all AI-filled columns per row (heuristic + LLM)
            # keyed by Python object id since rows are held in memory
            row_fills: Dict[int, List[str]] = {}

            # ── Step 3a: rule-based pre-fill (zero LLM cost) ─────────────
            now = datetime.utcnow()
            model_used_heuristic = "heuristic"
            for row_obj in rows:
                rec = {f: getattr(row_obj, f, None) for f in field_names if f not in _skip}
                fills = apply_heuristic_fills(rec, llm_source)
                if fills:
                    any_filled = False
                    for field_name, val in fills.items():
                        if hasattr(row_obj, field_name) and not getattr(row_obj, field_name):
                            setattr(row_obj, field_name, str(val))
                            any_filled = True
                            row_fills.setdefault(id(row_obj), []).append(field_name)
                            updates.append({
                                "run_id":          run_id,
                                "source":          source_label,
                                "app_id":          getattr(row_obj, "app_id", None),
                                "row_index":       row_obj.source_row_index,
                                "column_name":     field_name,
                                "original_value":  None,
                                "predicted_value": str(val),
                                "confidence":      0.85,
                                "llm_model":       model_used_heuristic,
                                "predicted_at":    now,
                            })
                    if any_filled:
                        row_obj.last_updated = 'Yes'
            # Flush heuristic fills so subsequent null_fields check sees them
            db.session.flush()

            # ── Step 3b: LLM for remaining null fields ────────────────────
            candidates: List[Tuple[Any, Dict[str, Any]]] = []
            for row_obj in rows:
                rec = {
                    f: getattr(row_obj, f, None)
                    for f in field_names
                    if f not in _skip
                }
                if _null_fields(rec):
                    candidates.append((row_obj, rec))

            if not candidates:
                logger.info("[%s] All fields filled by heuristics — skipping LLM", source_label)
            else:
                logger.info(
                    "[%s] %d/%d DB rows still have null fields after heuristics — sending to LLM",
                    source_label, len(candidates), len(rows),
                )

                all_records = [rec for _, rec in candidates]
                try:
                    batch_results = OllamaService.predict_missing_fields_batch(
                        all_records, source=llm_source, batch_size=20
                    )

                    model_used = OllamaService.get_selected_model()

                    for (row_obj, original_rec), (predictions, pred_cols, confidence_map) in zip(
                        candidates, batch_results
                    ):
                        if not predictions:
                            continue

                        any_updated = False
                        for field_name, predicted_val in predictions.items():
                            if predicted_val is None:
                                continue
                            if not hasattr(row_obj, field_name):
                                continue
                            setattr(row_obj, field_name, str(predicted_val))
                            any_updated = True
                            row_fills.setdefault(id(row_obj), []).append(field_name)
                            updates.append({
                                "run_id":          run_id,
                                "source":          source_label,
                                "app_id":          getattr(row_obj, "app_id", None),
                                "row_index":       row_obj.source_row_index,
                                "column_name":     field_name,
                                "original_value":  original_rec.get(field_name),
                                "predicted_value": str(predicted_val),
                                "confidence":      confidence_map.get(field_name, 0.75),
                                "llm_model":       model_used,
                                "predicted_at":    datetime.utcnow(),
                            })

                        if any_updated:
                            row_obj.last_updated = 'Yes'
                            row_obj.ai_confidence = confidence_map

                except Exception as exc:
                    logger.error(
                        "[%s] Batch prediction error: %s\n%s",
                        source_label, exc, traceback.format_exc(),
                    )

            # ── Step 3c: persist updated_rows + ai_predicted_columns on every touched row ─
            for row_obj in rows:
                cols = row_fills.get(id(row_obj))
                if cols:
                    row_obj.updated_rows = {
                        "app_id":          getattr(row_obj, "app_id", None),
                        "updated_columns": cols,
                    }
                    # Merge heuristic + LLM fills into ai_predicted_columns
                    existing_ai = set(row_obj.ai_predicted_columns or [])
                    existing_ai.update(cols)
                    row_obj.ai_predicted_columns = list(existing_ai)

            db.session.flush()

        return updates

    # ------------------------------------------------------------------ #
    # Step 4 — Save column-level update traceability
    # ------------------------------------------------------------------ #

    @staticmethod
    def _save_column_updates(updates: List[Dict[str, Any]]) -> None:
        objs = [WorkspaceColumnUpdate(**u) for u in updates]
        db.session.bulk_save_objects(objs)
        db.session.flush()

    # ------------------------------------------------------------------ #
    # Step 4b — Cross-source sync: APP Name
    # ------------------------------------------------------------------ #

    @staticmethod
    def _sync_app_names_across_sources(run_id: int) -> List[Dict[str, Any]]:
        """
        After LLM prediction, propagate the canonical app_name across all three
        workspace tables for rows that share the same app_id.

        Authority order: CAST > Business > CORENT
        Any row with a known app_id but still-null app_name receives the canonical name.
        """
        sync_updates: List[Dict[str, Any]] = []
        now = datetime.utcnow()

        cast_rows   = WorkspaceCastRow.query.filter_by(run_id=run_id).all()
        corent_rows = WorkspaceCorentRow.query.filter_by(run_id=run_id).all()
        biz_rows    = WorkspaceBizRow.query.filter_by(run_id=run_id).all()

        # Build canonical name — CAST has highest authority
        canonical: Dict[str, str] = {}
        for r in corent_rows:
            if r.app_id and r.app_name:
                canonical.setdefault(r.app_id.upper(), r.app_name)
        for r in biz_rows:
            if r.app_id and r.app_name:
                canonical[r.app_id.upper()] = r.app_name  # BIZ overrides CORENT
        for r in cast_rows:
            if r.app_id and r.app_name:
                canonical[r.app_id.upper()] = r.app_name  # CAST is authoritative

        if not canonical:
            return sync_updates

        for row_list, source_label in [
            (cast_rows,   "CAST"),
            (corent_rows, "CORENT"),
            (biz_rows,    "Business"),
        ]:
            for row in row_list:
                if not row.app_id or row.app_name:
                    continue
                name = canonical.get(row.app_id.upper())
                if name:
                    row.app_name = name
                    row.last_updated = 'Yes'
                    # Merge into existing updated_rows if present
                    existing = row.updated_rows or {}
                    existing_cols = existing.get("updated_columns", [])
                    if "app_name" not in existing_cols:
                        existing_cols.append("app_name")
                    row.updated_rows = {
                        "app_id":          row.app_id,
                        "updated_columns": existing_cols,
                    }
                    sync_updates.append({
                        "run_id":          run_id,
                        "source":          source_label,
                        "app_id":          row.app_id,
                        "row_index":       row.source_row_index,
                        "column_name":     "app_name",
                        "original_value":  None,
                        "predicted_value": name,
                        "confidence":      0.95,
                        "llm_model":       "cross_sync",
                        "predicted_at":    now,
                    })

        db.session.flush()
        logger.info(
            "[cross_sync] app_name synced %d rows across CAST/CORENT/Business (run_id=%d)",
            len(sync_updates), run_id,
        )
        return sync_updates

    # ------------------------------------------------------------------ #
    # Step 4c — Cross-source sync: Architecture fields
    # ------------------------------------------------------------------ #

    @staticmethod
    def _sync_architecture_across_sources(run_id: int) -> List[Dict[str, Any]]:
        """
        Propagate architecture data between CAST (application_architecture) and
        CORENT (architecture_type) for rows that share the same app_id.

        CAST → CORENT if CORENT.architecture_type is null.
        CORENT → CAST if CAST.application_architecture is null.
        """
        sync_updates: List[Dict[str, Any]] = []
        now = datetime.utcnow()

        cast_rows   = WorkspaceCastRow.query.filter_by(run_id=run_id).all()
        corent_rows = WorkspaceCorentRow.query.filter_by(run_id=run_id).all()

        cast_by_app_id:   Dict[str, Any] = {r.app_id.upper(): r for r in cast_rows   if r.app_id}
        corent_by_app_id: Dict[str, Any] = {r.app_id.upper(): r for r in corent_rows if r.app_id}

        # CAST application_architecture → CORENT architecture_type
        for aid_upper, cast_row in cast_by_app_id.items():
            if not cast_row.application_architecture:
                continue
            corent_row = corent_by_app_id.get(aid_upper)
            if corent_row and not corent_row.architecture_type:
                corent_row.architecture_type = cast_row.application_architecture
                corent_row.last_updated = 'Yes'
                existing = corent_row.updated_rows or {}
                existing_cols = existing.get("updated_columns", [])
                if "architecture_type" not in existing_cols:
                    existing_cols.append("architecture_type")
                corent_row.updated_rows = {"app_id": corent_row.app_id, "updated_columns": existing_cols}
                sync_updates.append({
                    "run_id": run_id, "source": "CORENT",
                    "app_id": corent_row.app_id,
                    "row_index": corent_row.source_row_index,
                    "column_name": "architecture_type",
                    "original_value": None,
                    "predicted_value": cast_row.application_architecture,
                    "confidence": 0.90, "llm_model": "cross_sync", "predicted_at": now,
                })

        # CORENT architecture_type → CAST application_architecture
        for aid_upper, corent_row in corent_by_app_id.items():
            if not corent_row.architecture_type:
                continue
            cast_row = cast_by_app_id.get(aid_upper)
            if cast_row and not cast_row.application_architecture:
                cast_row.application_architecture = corent_row.architecture_type
                cast_row.last_updated = 'Yes'
                existing = cast_row.updated_rows or {}
                existing_cols = existing.get("updated_columns", [])
                if "application_architecture" not in existing_cols:
                    existing_cols.append("application_architecture")
                cast_row.updated_rows = {"app_id": cast_row.app_id, "updated_columns": existing_cols}
                sync_updates.append({
                    "run_id": run_id, "source": "CAST",
                    "app_id": cast_row.app_id,
                    "row_index": cast_row.source_row_index,
                    "column_name": "application_architecture",
                    "original_value": None,
                    "predicted_value": corent_row.architecture_type,
                    "confidence": 0.90, "llm_model": "cross_sync", "predicted_at": now,
                })

        db.session.flush()
        logger.info(
            "[cross_sync] architecture synced %d rows CAST↔CORENT (run_id=%d)",
            len(sync_updates), run_id,
        )
        return sync_updates

    # ------------------------------------------------------------------ #
    # Step 5 — Correlate entirely from DB rows
    # ------------------------------------------------------------------ #

    @staticmethod
    def _correlate_from_db(run_id: int) -> Tuple[int, float]:
        """
        Build WorkspaceCorrelation records querying workspace row tables.

        Join strategy (CAST is anchor, three fallback levels per join):
          CAST ↔ CORENT:
            1. app_id exact match          (confidence weight 1.0)
            2. server_name exact match     (confidence weight 0.85)
            3. normalized app_name match   (confidence weight 0.70)
          CAST ↔ Business:
            1. app_id exact match          (confidence weight 1.0)
            2. normalized app_name match   (confidence weight 0.75)
        """
        cast_rows   = WorkspaceCastRow.query.filter_by(run_id=run_id).all()
        corent_rows = WorkspaceCorentRow.query.filter_by(run_id=run_id).all()
        biz_rows    = WorkspaceBizRow.query.filter_by(run_id=run_id).all()

        # --- exact key lookups ---
        corent_by_app_id: Dict[str, Any] = {
            r.app_id.upper(): r for r in corent_rows if r.app_id
        }
        corent_by_server: Dict[str, Any] = {
            r.server_name.upper(): r for r in corent_rows if r.server_name
        }
        biz_by_app_id: Dict[str, Any] = {
            r.app_id.upper(): r for r in biz_rows if r.app_id
        }

        # --- normalized app_name lookups (fuzzy fallback) ---
        corent_by_app_name: Dict[str, Any] = {}
        for r in corent_rows:
            norm = _normalize_app_name(r.app_name)
            if norm:
                corent_by_app_name.setdefault(norm, r)

        biz_by_app_name: Dict[str, Any] = {}
        for r in biz_rows:
            norm = _normalize_app_name(r.app_name)
            if norm:
                biz_by_app_name.setdefault(norm, r)

        correlations: List[WorkspaceCorrelation] = []
        matched = 0
        total   = max(len(cast_rows), 1)

        for cast_row in cast_rows:
            app_id  = cast_row.app_id
            sn_cast = cast_row.server_name

            # ── Match CORENT (3 levels) ──────────────────────────────────
            corent_row  = None
            corent_conf = 0.0
            if app_id:
                corent_row = corent_by_app_id.get(app_id.upper())
                if corent_row:
                    corent_conf = 1.0
            if corent_row is None and sn_cast:
                corent_row = corent_by_server.get(sn_cast.upper())
                if corent_row:
                    corent_conf = 0.85
            if corent_row is None and cast_row.app_name:
                corent_row = corent_by_app_name.get(_normalize_app_name(cast_row.app_name))
                if corent_row:
                    corent_conf = 0.70

            # ── Match Business (2 levels) ────────────────────────────────
            biz_row  = None
            biz_conf = 0.0
            if app_id:
                biz_row = biz_by_app_id.get(app_id.upper())
                if biz_row:
                    biz_conf = 1.0
            if biz_row is None and cast_row.app_name:
                biz_row = biz_by_app_name.get(_normalize_app_name(cast_row.app_name))
                if biz_row:
                    biz_conf = 0.75

            # ── Determine match type & confidence ────────────────────────
            if corent_row and biz_row:
                match_type       = "three_way"
                match_confidence = round((corent_conf + biz_conf) / 2, 2)
            elif biz_row:
                match_type       = "cast_biz"
                match_confidence = round(biz_conf * 0.85, 2)
            elif corent_row:
                match_type       = "cast_corent"
                match_confidence = round(corent_conf * 0.80, 2)
            else:
                match_type       = "unmatched"
                match_confidence = 0.0

            if match_type != "unmatched":
                matched += 1

            cloud_suitability = cast_row.cloud_suitability or (
                corent_row.cloud_suitability if corent_row else None
            )

            # Prefer the most-resolved app_name across all matched rows
            resolved_app_name = (
                cast_row.app_name
                or (corent_row.app_name if corent_row else None)
                or (biz_row.app_name    if biz_row    else None)
            )

            correlations.append(WorkspaceCorrelation(
                run_id=run_id,
                app_id=app_id,
                app_name=resolved_app_name,
                match_type=match_type,
                match_confidence=match_confidence,
                cast_server_name=sn_cast,
                corent_server_name=corent_row.server_name if corent_row else None,
                biz_platform_host=biz_row.platform_host   if biz_row    else None,
                cloud_suitability=cloud_suitability,
            ))

        if correlations:
            db.session.bulk_save_objects(correlations)
            db.session.flush()

        match_pct = round(matched / total * 100, 2)
        logger.info(
            "[correlate_from_db] run_id=%d: %d/%d rows matched (%.1f%%)",
            run_id, matched, total, match_pct,
        )
        return matched, match_pct

    # ------------------------------------------------------------------ #
    # Main entry point
    # ------------------------------------------------------------------ #

    @classmethod
    def run_workspace_pipeline(cls, app: Any) -> Dict[str, Any]:
        """
        New DB-centric pipeline:
          1. Read source Excel files directly (no copy to UpdatedData)
          2. Bulk-insert raw rows (last_updated='No')
          3. LLM-predict null fields per source; UPDATE DB rows in-place
             (last_updated='Yes' for rows with ≥1 AI fill)
          4. Persist WorkspaceColumnUpdate traceability rows
          5. Correlate from DB (no DataFrames needed)
          6. Finalise WorkspaceRun record
        """
        # ── Skip-if-unchanged: reuse last successful run when Excel files
        #    have not been modified since the previous run ─────────────────
        excel_hash = cls._compute_excel_hash()
        with app.app_context():
            last_done = (
                WorkspaceRun.query
                .filter_by(status="done")
                .order_by(WorkspaceRun.id.desc())
                .first()
            )
            if (
                last_done
                and getattr(last_done, "source_files_hash", None) == excel_hash
                and last_done.cast_rows
            ):
                logger.info(
                    "Excel files unchanged (hash=%s) — reusing run_id=%d",
                    excel_hash, last_done.id,
                )
                return {
                    "run_id":            last_done.id,
                    "matched_count":     last_done.matched_count,
                    "match_pct":         last_done.match_pct,
                    "cast_rows":         last_done.cast_rows,
                    "corent_rows":       last_done.corent_rows,
                    "biz_rows":          last_done.biz_rows,
                    "cells_predicted":   {
                        "CAST":     last_done.cast_predicted,
                        "CORENT":   last_done.corent_predicted,
                        "Business": last_done.biz_predicted,
                        "total":    last_done.cast_predicted + last_done.corent_predicted + last_done.biz_predicted,
                    },
                    "apps_with_ai_fill": last_done.cast_predicted + last_done.corent_predicted,
                    "llm_model":         last_done.llm_model,
                    "status":            "done",
                    "cached":            True,
                }

        with app.app_context():
            run = WorkspaceRun(
                status="running",
                llm_model=OllamaService.get_selected_model(),
                source_files_hash=excel_hash,
            )
            db.session.add(run)
            db.session.commit()
            run_id = run.id

        try:
            # ── Step 1: read source files ─────────────────────────────────
            cast_df   = cls._read_excel(_CAST_SRC,   _CAST_SHEET)
            corent_df = cls._read_excel(_CORENT_SRC, _CORENT_SHEET)
            biz_df    = cls._read_excel(_BIZ_SRC,    _BIZ_SHEET)

            # ── Step 2: load raw rows to DB ───────────────────────────────
            with app.app_context():
                cast_count   = cls._load_cast_rows(cast_df,   run_id)
                corent_count = cls._load_corent_rows(corent_df, run_id)
                biz_count    = cls._load_biz_rows(biz_df,     run_id)
                db.session.commit()
            logger.info(
                "run_id=%d: raw rows loaded CAST=%d CORENT=%d Biz=%d",
                run_id, cast_count, corent_count, biz_count,
            )

            # ── Step 3: predict nulls → UPDATE DB rows per source ─────────
            all_updates: List[Dict[str, Any]] = []
            for source_label, model_class, col_map in [
                ("CAST",     WorkspaceCastRow,   _CAST_COL_MAP),
                ("CORENT",   WorkspaceCorentRow, _CORENT_COL_MAP),
                ("Business", WorkspaceBizRow,    _BIZ_COL_MAP),
            ]:
                try:
                    updates = cls._predict_and_update_db(
                        model_class,
                        run_id,
                        list(col_map.values()),
                        source_label,
                        app,
                    )
                    all_updates.extend(updates)
                    with app.app_context():
                        db.session.commit()
                except Exception as exc:
                    logger.error(
                        "Prediction error for %s: %s\n%s",
                        source_label, exc, traceback.format_exc(),
                    )

            # ── Steps 4b/4c: cross-source sync (app_name + architecture) ─
            with app.app_context():
                sync_name_updates = cls._sync_app_names_across_sources(run_id)
                sync_arch_updates = cls._sync_architecture_across_sources(run_id)
                all_updates.extend(sync_name_updates)
                all_updates.extend(sync_arch_updates)
                if sync_name_updates or sync_arch_updates:
                    db.session.commit()

            # ── Steps 4 & 5: traceability + correlate ────────────────────
            with app.app_context():
                cast_pred   = sum(1 for u in all_updates if u["source"] == "CAST")
                corent_pred = sum(1 for u in all_updates if u["source"] == "CORENT")
                biz_pred    = sum(1 for u in all_updates if u["source"] == "Business")

                cls._save_column_updates(all_updates)

                matched, match_pct = cls._correlate_from_db(run_id)

                apps_with_ai_fill = len(set(
                    (u["source"], u["row_index"]) for u in all_updates
                ))

                run = db.session.get(WorkspaceRun, run_id)
                run.status           = "done"
                run.finished_at      = datetime.utcnow()
                run.cast_rows        = cast_count
                run.corent_rows      = corent_count
                run.biz_rows         = biz_count
                run.cast_predicted   = cast_pred
                run.corent_predicted = corent_pred
                run.biz_predicted    = biz_pred
                run.matched_count    = matched
                run.match_pct        = match_pct
                db.session.commit()

            logger.info(
                "workspace_pipeline run_id=%d done: CAST=%d CORENT=%d Biz=%d "
                "matched=%d (%.1f%%) ai_cells=%d",
                run_id, cast_count, corent_count, biz_count,
                matched, match_pct, len(all_updates),
            )

            return {
                "run_id":            run_id,
                "matched_count":     matched,
                "match_pct":         match_pct,
                "cast_rows":         cast_count,
                "corent_rows":       corent_count,
                "biz_rows":          biz_count,
                "cells_predicted":   {
                    "CAST":     cast_pred,
                    "CORENT":   corent_pred,
                    "Business": biz_pred,
                    "total":    len(all_updates),
                },
                "apps_with_ai_fill": apps_with_ai_fill,
                "llm_model":         OllamaService.get_selected_model(),
                "status":            "done",
            }

        except Exception as exc:
            err = traceback.format_exc()
            logger.error("workspace_pipeline failed: %s\n%s", exc, err)
            with app.app_context():
                run = db.session.get(WorkspaceRun, run_id)
                if run:
                    run.status       = "failed"
                    run.error_detail = err[:4000]
                    run.finished_at  = datetime.utcnow()
                    db.session.commit()
            return {"run_id": run_id, "status": "failed", "error": str(exc)}
