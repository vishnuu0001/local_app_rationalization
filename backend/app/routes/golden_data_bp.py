"""
Golden Data Blueprint
Endpoints:
  POST /api/golden-data/generate          – generate workbook, save to UpdatedData/, return preview JSON
  GET  /api/golden-data/preview           – preview-only (no workbook rebuild)
  GET  /api/golden-data/download          – stream UpdatedData/APRAttributes.xlsx

  GET  /api/golden-data/records           – list all GoldenData DB records
  POST /api/golden-data/records           – create a GoldenData DB record
  GET  /api/golden-data/records/<app_id>  – get a single record by app_id
  PUT  /api/golden-data/records/<app_id>  – update a record
  DELETE /api/golden-data/records/<app_id> – delete a record
"""

from flask import Blueprint, jsonify, send_file, current_app, request
from flask_cors import cross_origin
from app import db
from app.models.golden_data import GoldenData
from app.services.golden_data_service import (
    generate_golden_data, get_preview_data, regenerate_excel_from_db, _OUTPUT_PATH
)

golden_data_bp = Blueprint("golden_data", __name__, url_prefix="/api/golden-data")


@golden_data_bp.route("/generate", methods=["POST"])
def generate():
    """
    Generate the populated APRAttributes workbook from CORENT + CAST DB.
    Saves to UpdatedData/APRAttributes.xlsx and returns a JSON preview.
    """
    try:
        result = generate_golden_data()
        if result.get("error"):
            return jsonify({"success": False, "message": result["error"]}), 400

        return jsonify({
            "success": True,
            "row_count": result["row_count"],
            "preview_headers": result["preview_headers"],
            "preview_rows": result["preview_rows"],
            "missing_cast": result["missing_cast"],
            "output_path": result.get("output_path", ""),
            "message": (
                f"Generated {result['row_count']} rows. "
                f"Saved to UpdatedData/APRAttributes.xlsx. "
                f"{len(result['missing_cast'])} app(s) had no CAST data."
            ),
        }), 200

    except FileNotFoundError as exc:
        current_app.logger.error("Golden Data – template missing: %s", exc)
        return jsonify({"success": False, "message": str(exc)}), 500
    except Exception as exc:
        current_app.logger.exception("Golden Data – generate failed")
        return jsonify({"success": False, "message": str(exc)}), 500


@golden_data_bp.route("/preview", methods=["GET"])
def preview():
    """Return a lightweight preview of the data (no workbook generation)."""
    try:
        result = get_preview_data()
        return jsonify({"success": True, **result}), 200
    except Exception as exc:
        current_app.logger.exception("Golden Data – preview failed")
        return jsonify({"success": False, "message": str(exc)}), 500


@golden_data_bp.route("/download", methods=["GET"])
def download():
    """
    Serve UpdatedData/APRAttributes.xlsx.
    If it doesn't exist yet, generate it on-the-fly.
    """
    if not _OUTPUT_PATH.exists():
        try:
            result = generate_golden_data()
            if result.get("error"):
                return jsonify({"success": False, "message": result["error"]}), 400
        except Exception as exc:
            current_app.logger.exception("Golden Data – on-demand generate failed")
            return jsonify({"success": False, "message": str(exc)}), 500

    return send_file(
        str(_OUTPUT_PATH),
        as_attachment=True,
        download_name="APRAttributes.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@golden_data_bp.route("/regenerate-excel", methods=["POST"])
@cross_origin()
def regenerate_excel():
    """
    Rebuild APRAttributes.xlsx from the current GoldenData DB state.
    Use this after editing rows to bake user changes into the Excel file.
    """
    try:
        result = regenerate_excel_from_db()
        if result.get("error"):
            return jsonify({"success": False, "message": result["error"]}), 400
        return jsonify({
            "success": True,
            "row_count": result["row_count"],
            "message": f"Excel regenerated from {result['row_count']} DB records.",
        }), 200
    except FileNotFoundError as exc:
        return jsonify({"success": False, "message": str(exc)}), 500
    except Exception as exc:
        current_app.logger.exception("Golden Data – regenerate-excel failed")
        return jsonify({"success": False, "message": str(exc)}), 500


@golden_data_bp.route("/clear", methods=["POST"])
def clear():
    """
    Delete all GoldenData DB records AND remove UpdatedData/APRAttributes.xlsx.
    """
    try:
        # 1. Delete all DB records
        deleted_rows = GoldenData.query.delete()
        db.session.commit()

        # 2. Delete the generated Excel file
        file_deleted = False
        if _OUTPUT_PATH.exists():
            _OUTPUT_PATH.unlink()
            file_deleted = True

        return jsonify({
            "success": True,
            "message": f"Cleared {deleted_rows} DB record(s)."
                       + (" Excel file deleted." if file_deleted else " No Excel file to delete."),
        }), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Golden Data – clear failed")
        return jsonify({"success": False, "message": str(exc)}), 500


# ── Writable fields (excludes id / timestamps / ai_filled_cols) ────────────
_FIELDS = [
    'app_id', 'app_name', 'server_type', 'operating_system', 'cpu_core',
    'memory', 'internal_storage', 'external_storage', 'storage_type',
    'db_storage', 'db_engine', 'environment_install_type',
    'virtualization_attributes', 'compute_server_hardware_architecture',
    'application_stability', 'virtualization_state', 'storage_decomposition',
    'flash_storage_used', 'cpu_requirement', 'memory_ram_requirement',
    'mainframe_dependency', 'desktop_dependency',
    'app_os_platform_cloud_suitability', 'database_cloud_readiness',
    'integration_middleware_cloud_readiness', 'application_architecture',
    'application_hardware_dependency', 'app_cots_vs_non_cots',
    'source_code_availability', 'programming_language', 'component_coupling',
    'cloud_suitability', 'volume_external_dependencies',
    'app_service_api_readiness', 'app_load_predictability_elasticity',
    'degree_of_code_protocols', 'code_design',
    'application_code_complexity_volume',
    'financially_optimizable_hardware_usage',
    'distributed_architecture_design',
    'latency_requirements', 'ubiquitous_access_requirements',
    # Survey fields
    'level_of_data_residency_compliance', 'data_classification',
    'app_regulatory_contractual_requirements', 'impact_due_to_data_loss',
    'financial_impact_due_to_unavailability', 'business_criticality',
    'customer_facing', 'application_status_lifecycle_state',
    'availability_requirements', 'support_level',
    'business_function_readiness', 'level_of_internal_governance',
    'no_of_internal_users', 'no_of_external_users',
    'estimated_app_growth', 'impact_to_users',
    # Infra / SLA
    'no_of_production_environments', 'no_of_non_production_environments',
    'ha_dr_requirements', 'rto_requirements', 'rpo_requirements',
    'deployment_geography',
]


@golden_data_bp.route("/records", methods=["GET"])
@cross_origin()
def list_records():
    """Return all GoldenData records (paginated via ?page=&per_page=)."""
    page     = request.args.get('page',     1,   type=int)
    per_page = request.args.get('per_page', 100, type=int)
    search   = request.args.get('search',   '',  type=str).strip()

    query = GoldenData.query
    if search:
        query = query.filter(
            db.or_(
                GoldenData.app_id.ilike(f'%{search}%'),
                GoldenData.app_name.ilike(f'%{search}%'),
            )
        )

    pagination = query.order_by(GoldenData.app_id).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'status':    'success',
        'total':     pagination.total,
        'page':      pagination.page,
        'per_page':  pagination.per_page,
        'pages':     pagination.pages,
        'records':   [r.to_dict() for r in pagination.items],
    }), 200


@golden_data_bp.route("/records", methods=["POST"])
@cross_origin()
def create_record():
    """Create a new GoldenData record."""
    body = request.get_json(silent=True) or {}
    if not body.get('app_id'):
        return jsonify({'status': 'error', 'message': 'app_id is required'}), 400

    if GoldenData.query.filter_by(app_id=body['app_id']).first():
        return jsonify({'status': 'error', 'message': f"app_id '{body['app_id']}' already exists"}), 409

    record = GoldenData(**{f: body.get(f) for f in _FIELDS})
    db.session.add(record)
    db.session.commit()
    return jsonify({'status': 'success', 'record': record.to_dict()}), 201


@golden_data_bp.route("/records/<string:app_id>", methods=["GET"])
@cross_origin()
def get_record(app_id):
    """Fetch a single GoldenData record by app_id."""
    record = GoldenData.query.filter_by(app_id=app_id).first()
    if not record:
        return jsonify({'status': 'not_found', 'message': f"No record for app_id '{app_id}'"}), 404
    return jsonify({'status': 'success', 'record': record.to_dict()}), 200


@golden_data_bp.route("/records/<string:app_id>", methods=["PUT"])
@cross_origin()
def update_record(app_id):
    """Update an existing GoldenData record."""
    record = GoldenData.query.filter_by(app_id=app_id).first()
    if not record:
        return jsonify({'status': 'not_found', 'message': f"No record for app_id '{app_id}'"}), 404

    body = request.get_json(silent=True) or {}
    for field in _FIELDS:
        if field in body and field != 'app_id':   # app_id is the key – don't overwrite
            setattr(record, field, body[field])

    db.session.commit()
    return jsonify({'status': 'success', 'record': record.to_dict()}), 200


@golden_data_bp.route("/records/<string:app_id>", methods=["DELETE"])
@cross_origin()
def delete_record(app_id):
    """Delete a GoldenData record."""
    record = GoldenData.query.filter_by(app_id=app_id).first()
    if not record:
        return jsonify({'status': 'not_found', 'message': f"No record for app_id '{app_id}'"}), 404

    db.session.delete(record)
    db.session.commit()
    return jsonify({'status': 'success', 'message': f"Record '{app_id}' deleted"}), 200


@golden_data_bp.route("/records/bulk", methods=["POST"])
@cross_origin()
def bulk_upsert():
    """
    Bulk upsert GoldenData records.
    Body: { "records": [ { app_id, ... }, ... ] }
    Existing app_ids are updated; new ones are inserted.
    """
    body    = request.get_json(silent=True) or {}
    records = body.get('records', [])
    if not records:
        return jsonify({'status': 'error', 'message': 'No records provided'}), 400

    created = updated = 0
    for item in records:
        if not item.get('app_id'):
            continue
        existing = GoldenData.query.filter_by(app_id=item['app_id']).first()
        if existing:
            for field in _FIELDS:
                if field in item and field != 'app_id':
                    setattr(existing, field, item[field])
            updated += 1
        else:
            db.session.add(GoldenData(**{f: item.get(f) for f in _FIELDS}))
            created += 1

    db.session.commit()
    return jsonify({
        'status':  'success',
        'created': created,
        'updated': updated,
        'total':   created + updated,
    }), 200
