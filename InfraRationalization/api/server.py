"""
api/server.py
InfraRationalization FastAPI backend.

Endpoints:
  GET    /api/health                  — liveness check
  GET    /api/auth/session            — validate JWT and return session info

  POST   /api/scans/start             — trigger a live infrastructure scan
  GET    /api/scans/jobs              — list in-memory scan jobs (running + recent)
  GET    /api/scans/jobs/{scan_id}    — get live scan job status
  GET    /api/scans/jobs/{scan_id}/stream — SSE real-time progress stream
  GET    /api/scans/jobs/{scan_id}/report — get completed scan report

  GET    /api/scans                   — list all saved (persisted) scans
  POST   /api/scans                   — save a new scan (JSON body, manual upload)
  GET    /api/scans/{scan_id}         — get scan by id
  DELETE /api/scans/{scan_id}        — delete scan
  GET    /api/template               — download empty JSON scan template

Serves React SPA (frontend/dist) on all non-/api paths.
Port: 8083
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import queue
import time
import uuid
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# Scanner imports (optional — disabled gracefully if deps not installed)
try:
    from scanner.orchestrator import Orchestrator
    from scanner.models import ScanTarget
    _ORCHESTRATOR: Orchestrator | None = None

    def _get_orchestrator() -> Orchestrator:
        global _ORCHESTRATOR
        if _ORCHESTRATOR is None:
            _ORCHESTRATOR = Orchestrator(reports_dir=str(_REPORTS_DIR_LAZY()))
        return _ORCHESTRATOR

    SCANNER_AVAILABLE = True
except Exception as _scan_import_err:
    logging.getLogger(__name__).warning(
        "Scanner not available: %s", _scan_import_err
    )
    SCANNER_AVAILABLE = False

    def _get_orchestrator():  # type: ignore[misc]
        raise HTTPException(status_code=503, detail="Scanner dependencies not installed")


def _REPORTS_DIR_LAZY() -> Path:
    return Path(__file__).resolve().parent.parent / "reports"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INFRA_SCAN_APP = "INFRA_SCAN"

app = FastAPI(
    title="InfraRationalization API",
    description="Infrastructure feasibility analysis and cloud migration planning",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Serve React SPA ─────────────────────────────────────────────────────────
_DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST_DIR.exists():
    _assets_dir = _DIST_DIR / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/favicon.ico", include_in_schema=False)
    async def _favicon():
        ico = _DIST_DIR / "favicon.ico"
        return FileResponse(str(ico)) if ico.exists() else HTMLResponse("", status_code=204)

    @app.exception_handler(StarletteHTTPException)
    async def _spa_or_error(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404 and not request.url.path.startswith("/api"):
            return FileResponse(str(_DIST_DIR / "index.html"))
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    @app.get("/", include_in_schema=False)
    async def _index():
        return FileResponse(str(_DIST_DIR / "index.html"))


# ─── Scan report storage ──────────────────────────────────────────────────────
_REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
_REPORTS_DIR.mkdir(exist_ok=True)


# ─── Auth helpers ─────────────────────────────────────────────────────────────
def _auth_required() -> bool:
    return os.getenv("AUTH_REQUIRED", "true").lower() in {"1", "true", "yes"}


def _token_secret() -> str:
    return os.getenv("AUTH_TOKEN_SECRET") or "change-this-auth-token-secret-in-production"


def _b64url_decode(text: str) -> bytes:
    padding = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode((text + padding).encode("ascii"))


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _extract_bearer_token(authorization_header: str) -> str | None:
    if not authorization_header:
        return None
    parts = authorization_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


def _decode_access_token(token: str) -> dict:
    if not token:
        raise ValueError("Missing token")
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "v1":
        raise ValueError("Malformed token")
    payload_encoded = parts[1]
    expected_signature = _b64url_encode(
        hmac.new(
            _token_secret().encode("utf-8"),
            payload_encoded.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    )
    if not hmac.compare_digest(expected_signature, parts[2]):
        raise ValueError("Invalid token signature")
    payload = json.loads(_b64url_decode(payload_encoded).decode("utf-8"))
    if payload.get("typ") != "access":
        raise ValueError("Invalid token type")
    exp = int(payload.get("exp", 0))
    if exp <= int(time.time()):
        raise ValueError("Token expired")
    return payload


@app.middleware("http")
async def enforce_auth(request: Request, call_next):
    path = request.url.path
    public_paths = {"/api/health", "/docs", "/openapi.json", "/redoc"}
    if not _auth_required() or not path.startswith("/api") or path in public_paths:
        return await call_next(request)
    token = _extract_bearer_token(request.headers.get("Authorization", ""))
    if not token:
        return JSONResponse(status_code=401, content={"error": "Authentication required"})
    try:
        payload = _decode_access_token(token)
    except ValueError as exc:
        return JSONResponse(status_code=401, content={"error": str(exc)})
    role = payload.get("role")
    apps = payload.get("apps") or []
    if role != "admin" and INFRA_SCAN_APP not in apps:
        return JSONResponse(
            status_code=403,
            content={"error": "Access denied for Infra Scan"},
        )
    request.state.auth = payload
    return await call_next(request)


# ─── API endpoints ────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "module": "InfraRationalization", "port": 8083}


@app.get("/api/auth/session")
async def get_session(request: Request):
    token = _extract_bearer_token(request.headers.get("Authorization", ""))
    if not token:
        return JSONResponse(status_code=401, content={"error": "No token"})
    try:
        payload = _decode_access_token(token)
    except ValueError as exc:
        return JSONResponse(status_code=401, content={"error": str(exc)})
    return {
        "authenticated": True,
        "user": {
            "username": payload.get("sub"),
            "role": payload.get("role"),
            "apps": payload.get("apps", []),
        },
    }


# ─── Scan index helpers ───────────────────────────────────────────────────────

def _scan_index_path() -> Path:
    return _REPORTS_DIR / "_index.json"


def _load_index() -> list:
    p = _scan_index_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_index(index: list) -> None:
    _scan_index_path().write_text(
        json.dumps(index, indent=2, default=str), encoding="utf-8"
    )


def _scan_path(scan_id: str) -> Path:
    return _REPORTS_DIR / f"{scan_id}.json"


# ─── Scan CRUD ────────────────────────────────────────────────────────────────

@app.get("/api/scans")
async def list_scans():
    return {"scans": _load_index()}


@app.post("/api/scans")
async def create_scan(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    scan_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    scan_data = {**body, "scan_id": scan_id, "created_at": now}
    _scan_path(scan_id).write_text(
        json.dumps(scan_data, indent=2, default=str), encoding="utf-8"
    )
    index = _load_index()
    index.insert(0, {
        "scan_id": scan_id,
        "created_at": now,
        "report_name": body.get("report_name", "Untitled Scan"),
        "source_environment": body.get("source_environment", "Unknown"),
        "target_cloud": body.get("target_cloud", "Unknown"),
        "total_servers": body.get("summary", {}).get("total_servers", 0),
    })
    _save_index(index)
    return {"scan_id": scan_id, "created_at": now}


@app.get("/api/scans/{scan_id}")
async def get_scan(scan_id: str):
    p = _scan_path(scan_id)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Scan not found")
    return json.loads(p.read_text(encoding="utf-8"))


@app.delete("/api/scans/{scan_id}")
async def delete_scan(scan_id: str):
    p = _scan_path(scan_id)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Scan not found")
    p.unlink()
    _save_index([s for s in _load_index() if s["scan_id"] != scan_id])
    return {"deleted": True}


@app.get("/api/template")
async def get_template():
    template = {
        "report_name": "My Infrastructure Assessment",
        "source_environment": "OnPrem",
        "target_cloud": "Azure",
        "region": "East US",
        "summary": {
            "total_servers": 12,
            "os_count": 4,
            "storage_tb": 2.84,
            "utilization_breakdown": {"underutilized": 10, "moderate": 2, "utilized": 0},
            "server_type": "Virtual",
            "boot_type": "BIOS",
            "ip_distribution_note": "25% of Servers assigned with Private IP & ISP IP.",
        },
        "cloud_readiness": {
            "cloud_ready": 12,
            "cloud_ready_with_effort": 0,
            "lift_and_shift": 2,
            "smart_shift": 0,
            "smart_shift_with_effort": 10,
            "paas_shift": 0,
            "paas_shift_with_effort": 0,
        },
        "capacity_planning": {
            "equivalence_match": {
                "total_servers": 12,
                "total_cpu_cores": 86,
                "total_ram_gb": 344,
                "total_disk_tb": 2.84,
            },
            "best_match": {
                "total_servers": 12,
                "total_cpu_cores": 40,
                "total_ram_gb": 120,
                "total_disk_tb": 2.84,
            },
        },
        "servers": [
            {
                "ip": "10.10.43.40",
                "name": "qaanalyser-FS",
                "os": "Ubuntu 24.04.2 LTS",
                "cpu_cores": 8,
                "ram_gb": 32,
                "disk_gb": 240,
                "utilization": "underutilized",
                "migration_strategy": "smart_shift_effort",
                "migration_recommendation": "OS Ubuntu 24.04.2 LTS not available in Cloud. Recommend Ubuntu 22.04 LTS.",
                "workloads": ["ApacheTomcat 9.0.102"],
            }
        ],
        "pricing_plans": [
            {
                "plan_name": "Pay As You Go",
                "equivalence_match_total_per_month": 1841,
                "best_match_total_per_month": 856,
                "flavors": [
                    {
                        "cloud_name": "OnPrem",
                        "flavor_name": "PowerEdge_R6615_8X32",
                        "os_name": "Red Hat 9.6",
                        "flavor_family": "General Purpose",
                        "ram_gb": 32,
                        "cpu_cores": 8,
                        "equivalence_servers": 3,
                        "equivalence_cost_per_month": 513.66,
                        "best_servers": 0,
                        "best_cost_per_month": 0.0,
                    }
                ],
            }
        ],
        "workload_consolidation": [
            {
                "workload_name": "MySQL",
                "current_server_count": 4,
                "recommended_server_count": 1,
                "instances": [
                    {
                        "server_ip": "10.10.43.41",
                        "server_name": "qaanalyser-db",
                        "version": "MySQL 8.4.5",
                        "location": "/usr/sbin",
                    }
                ],
            }
        ],
        "eos_advisories": {
            "operating_systems": [
                {
                    "server_ip": "10.10.43.44",
                    "server_name": "tesmaasqa-FS",
                    "os": "Red Hat Enterprise Linux 9.6",
                    "end_of_support": "2032-05-31",
                    "end_of_extended_support": "2035-05-31",
                    "migration_advisory": "Migrate to Red Hat Enterprise Linux 9.3 using Smart Migration with Service Effort.",
                }
            ],
            "workloads": [
                {
                    "server_name": "TESTMAASQA-214",
                    "server_ip": "10.10.43.43",
                    "workload": "ApacheTomcat 9.0.109",
                    "location": "D:\\MaaS\\Tomcat04-Common",
                    "end_of_support": "2027-03-31",
                    "end_of_extended_support": None,
                }
            ],
        },
    }
    return JSONResponse(
        content=template,
        headers={"Content-Disposition": 'attachment; filename="infra_scan_template.json"'},
    )


# ─── Live Scanner Endpoints ───────────────────────────────────────────────────

@app.post("/api/scans/start")
async def start_scan(request: Request):
    """
    Trigger a live network / cloud infrastructure scan.

    Body (all optional depending on provider):
      provider            : "onprem" | "aws" | "azure" | "gcp" | "multi"
      report_name         : str
      network_range       : "10.0.0.0/24"   (onprem)
      ssh_username        : str
      ssh_password        : str
      ssh_key_path        : str
      winrm_username      : str
      winrm_password      : str
      aws_access_key_id   : str
      aws_secret_access_key: str
      aws_regions         : ["us-east-1", ...]
      azure_tenant_id     : str
      azure_client_id     : str
      azure_client_secret : str
      azure_subscription_id: str
      gcp_project_id      : str
      gcp_service_account_json: str  (JSON string)
      gcp_regions         : ["us-central1", ...]
      deep_scan           : bool  (default true)
      port_scan           : bool  (default true)
      timeout_seconds     : int   (default 30)
    """
    if not SCANNER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scanner dependencies not installed")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    provider = body.get("provider", "onprem")
    report_name = body.get("report_name", f"Scan {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")

    target = ScanTarget(
        provider=provider,
        network_range=body.get("network_range", ""),
        ssh_username=body.get("ssh_username", ""),
        ssh_password=body.get("ssh_password", ""),
        ssh_key_path=body.get("ssh_key_path", ""),
        winrm_username=body.get("winrm_username", ""),
        winrm_password=body.get("winrm_password", ""),
        aws_access_key_id=body.get("aws_access_key_id", ""),
        aws_secret_access_key=body.get("aws_secret_access_key", ""),
        aws_regions=body.get("aws_regions") or ["us-east-1"],
        azure_tenant_id=body.get("azure_tenant_id", ""),
        azure_client_id=body.get("azure_client_id", ""),
        azure_client_secret=body.get("azure_client_secret", ""),
        azure_subscription_id=body.get("azure_subscription_id", ""),
        gcp_project_id=body.get("gcp_project_id", ""),
        gcp_service_account_json=body.get("gcp_service_account_json", ""),
        gcp_regions=body.get("gcp_regions") or ["us-central1"],
        deep_scan=body.get("deep_scan", True),
        port_scan=body.get("port_scan", True),
        timeout_seconds=int(body.get("timeout_seconds", 30)),
    )

    orch = _get_orchestrator()
    scan_id = orch.start_scan(target, report_name)
    return {"scan_id": scan_id, "report_name": report_name, "status": "pending"}


@app.get("/api/scans/jobs")
async def list_scan_jobs():
    """List all in-memory scan jobs (running, pending, recently completed)."""
    if not SCANNER_AVAILABLE:
        return {"jobs": []}
    orch = _get_orchestrator()
    return {"jobs": orch.list_jobs()}


@app.get("/api/scans/jobs/{scan_id}")
async def get_scan_job(scan_id: str):
    """Get live status of a scan job."""
    if not SCANNER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scanner not available")
    orch = _get_orchestrator()
    status = orch.get_status(scan_id)
    if not status:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return status


@app.get("/api/scans/jobs/{scan_id}/stream")
async def stream_scan_progress(scan_id: str, request: Request, token: str = ""):
    """
    Server-Sent Events stream for real-time scan progress.
    Accepts auth token via query param (?token=...) for EventSource compatibility.

    Sends: text/event-stream
      data: {"progress": 42, "message": "Scanning 10.0.0.5..."}
    """
    if not SCANNER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scanner not available")

    # Support token via query string for EventSource (which can't set headers)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header and token:
        auth_header = f"Bearer {token}"
    if _auth_required() and auth_header:
        try:
            _decode_access_token(_extract_bearer_token(auth_header) or "")
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc))

    orch = _get_orchestrator()
    status = orch.get_status(scan_id)
    if not status:
        raise HTTPException(status_code=404, detail="Scan job not found")

    event_queue: queue.Queue = queue.Queue(maxsize=200)

    def on_event(data: str) -> None:
        try:
            event_queue.put_nowait(data)
        except queue.Full:
            pass

    orch.subscribe_progress(scan_id, on_event)

    async def event_generator():
        try:
            while True:
                try:
                    data = event_queue.get_nowait()
                    yield f"data: {data}\n\n"
                    parsed = json.loads(data)
                    if parsed.get("progress", 0) >= 100:
                        break
                except queue.Empty:
                    # Check job status
                    job_status = orch.get_status(scan_id)
                    if job_status and job_status["status"] in ("completed", "failed"):
                        final = json.dumps({
                            "progress": 100 if job_status["status"] == "completed" else 0,
                            "message": job_status.get("progress_message", ""),
                            "status": job_status["status"],
                            "error": job_status.get("error"),
                        })
                        yield f"data: {final}\n\n"
                        break
                    yield ": keepalive\n\n"
                    await asyncio.sleep(0.5)
        finally:
            orch.unsubscribe_progress(scan_id, on_event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/scans/jobs/{scan_id}/report")
async def get_scan_report(scan_id: str):
    """Return the completed scan report JSON."""
    if not SCANNER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scanner not available")
    orch = _get_orchestrator()
    report = orch.get_report(scan_id)
    if not report:
        # Maybe it's a persisted scan (manual upload)
        p = _scan_path(scan_id)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        raise HTTPException(status_code=404, detail="Report not found")
    return report


if __name__ == "__main__":
    uvicorn.run("api.server:app", host="0.0.0.0", port=8083, reload=True)
