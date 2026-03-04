"""
Golden Data Blueprint
Endpoints:
  POST /api/golden-data/generate   – generate workbook, save to UpdatedData/, return preview JSON
  GET  /api/golden-data/preview    – preview-only (no workbook rebuild)
  GET  /api/golden-data/download   – stream UpdatedData/APRAttributes.xlsx
"""

from flask import Blueprint, jsonify, send_file, current_app
from app.services.golden_data_service import (
    generate_golden_data, get_preview_data, _OUTPUT_PATH
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


@golden_data_bp.route("/clear", methods=["POST"])
def clear():
    """
    Delete UpdatedData/APRAttributes.xlsx if it exists.
    """
    try:
        if _OUTPUT_PATH.exists():
            _OUTPUT_PATH.unlink()
            return jsonify({"success": True, "message": "Output file deleted."}), 200
        return jsonify({"success": True, "message": "No file to delete."}), 200
    except Exception as exc:
        current_app.logger.exception("Golden Data – clear failed")
        return jsonify({"success": False, "message": str(exc)}), 500
