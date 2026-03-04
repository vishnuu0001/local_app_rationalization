"""
Golden Data Service
-------------------
Fetches CorentData and CASTData from the DB, maps them to the
'Inputs from Sources' sheet in APRAttributes.xlsx (starting at row 6),
and returns both the populated workbook bytes and a preview payload.

Column mapping (row 5 = header row, row 6+ = data):
  Col 1  APP ID                              corent.app_id
  Col 2  List of Applications                corent.app_name
  Col 3  Server Type                         corent.server_type
  Col 4  Operating System                    corent.operating_system
  Col 5  CPU Core                            corent.cpu_core
  Col 6  Memory                              corent.memory
  Col 7  Internal Storage                    corent.internal_storage
  Col 8  External Storage                    corent.external_storage
  Col 9  Storage Type                        corent.storage_type
  Col 10 DB Storage                          corent.db_storage
  Col 11 DB Engine                           corent.db_engine
  Col 12 Environment (INSTALL TYPE)          corent.environment + " / " + corent.install_type
  Col 13 Virtualization Attributes           corent.virtualization_attributes
  Col 14 Compute/Server HW Architecture      corent.compute_server_hardware_architecture
  Col 15 Application Stability               corent.application_stability
  Col 16 Virtualization State                corent.virtualization_state
  Col 17 Storage Decomposition               corent.storage_decomposition
  Col 18 FLASH Storage Used                  corent.flash_storage_used
  Col 19 CPU Requirement                     corent.cpu_requirement
  Col 20 Memory (RAM) Requirement            corent.memory_ram_requirement
  Col 21 Mainframe Dependency                corent.mainframe_dependency
  Col 22 Desktop Dependency                  corent.desktop_dependency
  Col 23 App OS/Platform Cloud Suitability   corent.app_os_platform_cloud_suitability
  Col 24 Database Cloud Readiness            corent.database_cloud_readiness
  Col 25 Integration Middleware Cloud Ready  corent.integration_middleware_cloud_readiness
  Col 26 Application Architecture            cast.application_architecture
  Col 27 Application Hardware Dependency     corent.application_hardware_dependency
  Col 28 App COTS vs. Non-COTS              corent.app_cots_vs_non_cots
  Col 29 Source Code Availability            cast.source_code_availability
  Col 30 Programming Language               cast.programming_language
  Col 31 Component Coupling                 cast.component_coupling
  Col 32 Cloud Suitability (CORENT+CAST)    corent.cloud_suitability or cast.cloud_suitability
  Col 33 Volume External Dependencies       corent.volume_external_dependencies or cast.volume_external_dependencies
  Col 34 App Service/API Readiness          cast.app_service_api_readiness
  Col 35 App Load Predictability/Elasticity corent.app_load_predictability_elasticity
  Col 36 Degree of Code Protocols           cast.degree_of_code_protocols
  Col 37 Code Design                        cast.code_design
  Col 38 App-Code Complexity/Volume         cast.application_code_complexity_volume
  Col 39 Financially Optimizable HW Usage   corent.financially_optimizable_hardware_usage
  Col 40 Distributed Architecture Design    corent.distributed_architecture_design or cast.distributed_architecture_design
  Col 41 Latency Requirements               corent.latency_requirements
  Col 42 Ubiquitous Access Requirements     corent.ubiquitous_access_requirements
  Col 43-52 (SURVEY)                        blank
  Col 53 No. Production Environments        corent.no_production_environments
  Col 54 No. Non-Production Environments    corent.no_non_production_environments
  Col 55 HA/DR Requirements                 corent.ha_dr_requirements
  Col 56 (SURVEY)                           blank
  Col 57 RTO Requirements                   corent.rto_requirements
  Col 58 RPO Requirements                   corent.rpo_requirements
  Col 59 Deployment Geography               corent.deployment_geography
  Col 60-64 (SURVEY/other)                  blank
"""

import os
from pathlib import Path

import openpyxl
from openpyxl.styles import PatternFill, Alignment

from app.models.corent_data import CorentData
from app.models.cast import CASTData

# Paths
_TEMPLATE_PATH  = Path(__file__).resolve().parent.parent.parent / "data" / "APRAttributes.xlsx"
_OUTPUT_DIR     = Path(__file__).resolve().parent.parent.parent / "UpdatedData"
_OUTPUT_PATH    = _OUTPUT_DIR / "APRAttributes.xlsx"
_SHEET_NAME     = "Inputs from Sources"
_DATA_START_ROW = 6    # Row 5 = header, row 6+ = data
_MAX_PREVIEW_ROWS = 200


def _coalesce(*values):
    """Return first non-None, non-empty value."""
    for v in values:
        if v is not None and str(v).strip():
            return v
    return None


def _env_install(corent_row):
    """Combine environment + install_type into one cell value."""
    parts = [p for p in (corent_row.environment, corent_row.install_type) if p]
    return " / ".join(parts) if parts else None


def _build_row_values(corent_row, cast_row):
    """
    Return a list of 64 values in column order (index 0 = col 1).
    cast_row may be None when no CAST data exists for that app_id.
    """
    c = corent_row
    k = cast_row  # may be None

    def cast(attr):
        return getattr(k, attr, None) if k else None

    row = [None] * 64

    row[0]  = c.app_id
    row[1]  = c.app_name
    row[2]  = c.server_type
    row[3]  = c.operating_system
    row[4]  = c.cpu_core
    row[5]  = c.memory
    row[6]  = c.internal_storage
    row[7]  = c.external_storage
    row[8]  = c.storage_type
    row[9]  = c.db_storage
    row[10] = c.db_engine
    row[11] = _env_install(c)
    row[12] = c.virtualization_attributes
    row[13] = c.compute_server_hardware_architecture
    row[14] = c.application_stability
    row[15] = c.virtualization_state
    row[16] = c.storage_decomposition
    row[17] = c.flash_storage_used
    row[18] = c.cpu_requirement
    row[19] = c.memory_ram_requirement
    row[20] = c.mainframe_dependency
    row[21] = c.desktop_dependency
    row[22] = c.app_os_platform_cloud_suitability
    row[23] = c.database_cloud_readiness
    row[24] = c.integration_middleware_cloud_readiness
    row[25] = cast('application_architecture')           # CAST
    row[26] = c.application_hardware_dependency
    row[27] = c.app_cots_vs_non_cots
    row[28] = cast('source_code_availability')           # CAST
    row[29] = cast('programming_language')               # CAST
    row[30] = cast('component_coupling')                 # CAST
    row[31] = _coalesce(c.cloud_suitability, cast('cloud_suitability'))           # CORENT+CAST
    row[32] = _coalesce(c.volume_external_dependencies, cast('volume_external_dependencies'))  # CORENT+CAST
    row[33] = cast('app_service_api_readiness')          # CAST
    row[34] = c.app_load_predictability_elasticity
    row[35] = cast('degree_of_code_protocols')           # CAST
    row[36] = cast('code_design')                        # CAST
    row[37] = cast('application_code_complexity_volume') # CAST
    row[38] = c.financially_optimizable_hardware_usage
    row[39] = _coalesce(c.distributed_architecture_design, cast('distributed_architecture_design'))  # CORENT+CAST
    row[40] = c.latency_requirements
    row[41] = c.ubiquitous_access_requirements
    # 42-51 → SURVEY (blank)
    row[52] = c.no_production_environments
    row[53] = c.no_non_production_environments
    row[54] = c.ha_dr_requirements
    # 55 → SURVEY (blank)
    row[56] = c.rto_requirements
    row[57] = c.rpo_requirements
    row[58] = c.deployment_geography
    # 59-63 → SURVEY/other (blank)

    return row


def _get_column_headers():
    """Return the 64-column header list (row 5 labels)."""
    return [
        "APP ID", "List of Applications", "Server Type", "Operating System",
        "CPU Core", "Memory", "Internal Storage", "External Storage",
        "Storage Type", "DB Storage", "DB Engine", "Environment (INSTALL TYPE)",
        "Virtualization Attributes", "Compute / Server Hardware Architecture",
        "Application Stability", "Virtualization State", "Storage Decomposition",
        "FLASH Storage Used", "CPU Requirement", "Memory (RAM) Requirement",
        "Mainframe Dependency", "Desktop Dependency",
        "App OS / Platform Cloud Suitability", "Database Cloud Readiness",
        "Integration Middleware Cloud Readiness", "Application Architecture",
        "Application Hardware Dependency", "App COTS vs. Non-COTS Only",
        "Source Code Availability", "Programming Language", "Component Coupling",
        "Cloud Suitability", "Volume of External Dependencies",
        "App Service / API Readiness", "App Load Predictability / Elasticity",
        "Degree of Code Protocols", "Code Design",
        "Application-Code Complexity / Volume",
        "Financially Optimizable Hardware Usage",
        "Distributed Architecture Design or not",
        "Latency Requirements", "Ubiquitous Access Requirements",
        "Level of Data Residency Compliance", "Data Classification",
        "App Regulatory & Contractual Requirements",
        "Impact Due to Data Loss", "Financial Impact Due to Unavailability",
        "Business Criticality", "Customer Facing",
        "Application Status & Lifecycle State", "Availability Requirements",
        "Support Level", "No. of Production Environments",
        "No. of Non-Production Environments", "HA/DR Requirements",
        "Business Function Readiness", "RTO Requirements", "RPO Requirements",
        "Deployment Geography", "Level of Internal Governance",
        "No. of Internal Users", "No. of External Users",
        "Estimated App Growth", "Impact to Users",
    ]


def generate_golden_data():
    """
    1. shutil.copy2(template → UpdatedData/APRAttributes.xlsx)  — fast binary copy, all 16 sheets intact
    2. Load the copy in write mode
    3. Clear rows 6+ of 'Inputs from Sources', write DB rows
    4. Save ONCE to disk  (download endpoint serves from that file)
    """
    # ── 1. Fetch data ──────────────────────────────────────────────────────────
    corent_rows = CorentData.query.order_by(CorentData.app_id).all()
    if not corent_rows:
        return {
            "row_count": 0,
            "preview_headers": _get_column_headers(),
            "preview_rows": [],
            "missing_cast": [],
            "error": "No CORENT data found in the database.",
        }

    cast_index = {r.app_id: r for r in CASTData.query.all()}

    # ── 2. Copy template → UpdatedData/ ───────────────────────────────────────
    if not _TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found: {_TEMPLATE_PATH}")
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    import shutil as _shutil
    _shutil.copy2(str(_TEMPLATE_PATH), str(_OUTPUT_PATH))

    # ── 3. Load the copy (all 16 sheets) ──────────────────────────────────────
    wb = openpyxl.load_workbook(str(_OUTPUT_PATH))
    ws = wb[_SHEET_NAME]

    # ── 4. Clear existing data rows 6+ (keep header rows 1-5) ─────────────────
    if ws.max_row >= _DATA_START_ROW:
        for r in range(_DATA_START_ROW, ws.max_row + 1):
            for c in range(1, 65):
                ws.cell(row=r, column=c).value = None

    # ── 5. Write DB rows ───────────────────────────────────────────────────────
    missing_cast = []
    preview_rows = []
    cast_fill = PatternFill(start_color="EBF5FB", end_color="EBF5FB", fill_type="solid")

    for idx, corent_row in enumerate(corent_rows):
        cast_row = cast_index.get(corent_row.app_id)
        if cast_row is None:
            missing_cast.append(corent_row.app_id)

        values = _build_row_values(corent_row, cast_row)
        excel_row_num = _DATA_START_ROW + idx

        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=excel_row_num, column=col_idx, value=value)
            if cast_row and col_idx in {26, 29, 30, 31, 32, 33, 34, 36, 37, 38, 40}:
                cell.fill = cast_fill
            cell.alignment = Alignment(wrap_text=False, vertical="center")

        if idx < _MAX_PREVIEW_ROWS:
            preview_rows.append(values)

    # ── 6. Save ONCE to disk ───────────────────────────────────────────────────
    wb.save(str(_OUTPUT_PATH))

    return {
        "row_count": len(corent_rows),
        "preview_headers": _get_column_headers(),
        "preview_rows": preview_rows,
        "missing_cast": missing_cast,
        "output_path": str(_OUTPUT_PATH),
        "error": None,
    }


def get_preview_data():
    """
    Return preview data without generating the full workbook (lighter call).
    Used by the frontend to display data after generation.
    """
    corent_rows = CorentData.query.order_by(CorentData.app_id).all()
    cast_index = {r.app_id: r for r in CASTData.query.all()}

    preview_rows = []
    missing_cast = []

    for corent_row in corent_rows[:_MAX_PREVIEW_ROWS]:
        cast_row = cast_index.get(corent_row.app_id)
        if not cast_row:
            missing_cast.append(corent_row.app_id)
        preview_rows.append(_build_row_values(corent_row, cast_row))

    return {
        "row_count": len(corent_rows),
        "preview_headers": _get_column_headers(),
        "preview_rows": preview_rows,
        "missing_cast": missing_cast,
    }
