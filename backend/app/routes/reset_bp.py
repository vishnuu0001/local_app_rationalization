"""
Reset Blueprint
POST /api/reset  –  Wipe ALL data from every table, remove uploaded files,
                    and delete any generated Excel on app load.
"""

import os
from flask import Blueprint, jsonify, current_app
from flask_cors import cross_origin
from app import db
from app.models.golden_data import GoldenData
from app.models.correlation import CorrelationResult, MasterMatrixEntry
from app.models.analysis import AnalysisResult, RationalizationScenario
from app.models.pdf_report import PDFReport
from app.models.infrastructure import (
    Infrastructure, Server, Container, NetworkLink,
    InfrastructureDiscovery, BusinessCapabilities,
)
from app.models.code import CodeRepository, ArchitectureComponent, InternalDependency
from app.models.application import Application
from app.models.cast import (
    CASTAnalysis, ApplicationInventory, ApplicationClassification,
    InternalArchitecture, HighRiskApplication, CASTData,
)
from app.models.corent_data import CorentData
from app.models.industry_data import IndustryData, IndustryTemplate
from app.services.golden_data_service import _OUTPUT_PATH as GOLDEN_EXCEL_PATH

reset_bp = Blueprint("reset", __name__, url_prefix="/api")

# Deletion order respects FK constraints (children before parents).
# ALL tables are included — nothing is preserved.
_MODELS_TO_CLEAR = [
    MasterMatrixEntry,
    CorrelationResult,
    GoldenData,
    RationalizationScenario,
    AnalysisResult,
    PDFReport,
    BusinessCapabilities,
    InfrastructureDiscovery,
    ArchitectureComponent,
    InternalDependency,
    Application,
    CodeRepository,
    HighRiskApplication,
    ApplicationClassification,
    ApplicationInventory,
    InternalArchitecture,
    CASTAnalysis,
    Container,
    NetworkLink,
    Server,
    Infrastructure,
    CorentData,
    CASTData,
    IndustryData,
    IndustryTemplate,
]


@reset_bp.route("/reset", methods=["POST"])
@cross_origin()
def reset_all():
    """Wipe every table, uploaded files, and generated Excel."""
    deleted = {}
    try:
        # Clear the server_application join table first (no ORM model)
        db.session.execute(db.text("DELETE FROM server_application"))
        deleted["server_application"] = "cleared"

        for model in _MODELS_TO_CLEAR:
            table = model.__tablename__
            count = model.query.delete(synchronize_session=False)
            deleted[table] = count

        db.session.commit()

        # Remove uploaded files from disk
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "")
        files_removed = 0
        if upload_folder and os.path.isdir(upload_folder):
            for fname in os.listdir(upload_folder):
                fpath = os.path.join(upload_folder, fname)
                try:
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                        files_removed += 1
                except Exception:
                    pass
        deleted["uploaded_files"] = files_removed

        # Remove generated Golden Data Excel
        excel_deleted = False
        if GOLDEN_EXCEL_PATH.exists():
            GOLDEN_EXCEL_PATH.unlink()
            excel_deleted = True
        deleted["golden_excel_deleted"] = excel_deleted

        current_app.logger.info("App reset: %s", deleted)
        return jsonify({"success": True, "cleared": deleted}), 200

    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Reset failed")
        return jsonify({"success": False, "message": str(exc)}), 500
