"""
scanner/orchestrator.py
Central scan dispatcher. Manages ScanJob lifecycle, launches provider-specific
scanners in background threads, and aggregates results into a report.

Usage:
    from scanner.orchestrator import Orchestrator
    orch = Orchestrator(reports_dir="reports/")
    scan_id = orch.start_scan(target, report_name="My Scan")
    status  = orch.get_status(scan_id)
    report  = orch.get_report(scan_id)
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Generator

from .models import ScanJob, ScanTarget
from .report_builder import build_report

log = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, reports_dir: str = "reports") -> None:
        self._reports_dir = Path(reports_dir)
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, ScanJob] = {}
        self._lock = threading.Lock()

        # SSE subscribers: scan_id → list of queue-like callables
        self._subscribers: dict[str, list[Callable[[str], None]]] = {}

    # ── Public API ────────────────────────────────────────────────────────

    def start_scan(self, target: ScanTarget, report_name: str) -> str:
        scan_id = str(uuid.uuid4())
        job = ScanJob(
            scan_id=scan_id,
            report_name=report_name,
            target=target,
            status="pending",
        )
        with self._lock:
            self._jobs[scan_id] = job

        thread = threading.Thread(
            target=self._run_scan,
            args=(scan_id,),
            daemon=True,
            name=f"scan-{scan_id[:8]}",
        )
        thread.start()
        return scan_id

    def get_status(self, scan_id: str) -> dict[str, Any] | None:
        job = self._jobs.get(scan_id)
        if not job:
            return None
        return {
            "scan_id": job.scan_id,
            "report_name": job.report_name,
            "status": job.status,
            "progress": job.progress,
            "progress_message": job.progress_message,
            "error": job.error,
            "server_count": len(job.servers),
            "created_at": job.created_at,
            "completed_at": job.completed_at,
        }

    def list_jobs(self) -> list[dict[str, Any]]:
        return [self.get_status(jid) for jid in self._jobs]  # type: ignore[misc]

    def get_report(self, scan_id: str) -> dict | None:
        report_path = self._reports_dir / f"{scan_id}.json"
        if report_path.exists():
            with open(report_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return None

    def subscribe_progress(self, scan_id: str, callback: Callable[[str], None]) -> None:
        """Register a callback that will be called with SSE event strings."""
        with self._lock:
            self._subscribers.setdefault(scan_id, []).append(callback)

    def unsubscribe_progress(self, scan_id: str, callback: Callable[[str], None]) -> None:
        with self._lock:
            subs = self._subscribers.get(scan_id, [])
            if callback in subs:
                subs.remove(callback)

    # ── Internal ─────────────────────────────────────────────────────────

    def _update_job(self, scan_id: str, **kwargs: Any) -> None:
        with self._lock:
            job = self._jobs.get(scan_id)
            if job:
                for k, v in kwargs.items():
                    setattr(job, k, v)

    def _emit(self, scan_id: str, pct: int, msg: str) -> None:
        self._update_job(scan_id, progress=pct, progress_message=msg)
        event = json.dumps({"progress": pct, "message": msg})
        with self._lock:
            subs = list(self._subscribers.get(scan_id, []))
        for cb in subs:
            try:
                cb(event)
            except Exception:
                pass

    def _run_scan(self, scan_id: str) -> None:
        self._update_job(scan_id, status="running", progress=0, progress_message="Starting scan…")
        with self._lock:
            job = self._jobs[scan_id]
        target = job.target

        servers = []
        try:
            provider = target.provider.lower()

            def cb(pct: int, msg: str) -> None:
                self._emit(scan_id, pct, msg)

            if provider == "onprem":
                from .onprem import scan_onprem
                servers = scan_onprem(target, progress_cb=cb)

            elif provider == "aws":
                from .aws_scanner import scan_aws
                servers = scan_aws(target, progress_cb=cb)

            elif provider == "azure":
                from .azure_scanner import scan_azure
                servers = scan_azure(target, progress_cb=cb)

            elif provider == "gcp":
                from .gcp_scanner import scan_gcp
                servers = scan_gcp(target, progress_cb=cb)

            elif provider == "multi":
                # Scan all configured providers
                if target.network_range:
                    from .onprem import scan_onprem
                    self._emit(scan_id, 5, "Scanning on-premises network…")
                    servers += scan_onprem(target, progress_cb=lambda p, m: cb(5 + p // 4, m))

                if target.aws_access_key_id:
                    from .aws_scanner import scan_aws
                    self._emit(scan_id, 30, "Scanning AWS…")
                    servers += scan_aws(target, progress_cb=lambda p, m: cb(30 + p // 4, m))

                if target.azure_subscription_id:
                    from .azure_scanner import scan_azure
                    self._emit(scan_id, 55, "Scanning Azure…")
                    servers += scan_azure(target, progress_cb=lambda p, m: cb(55 + p // 4, m))

                if target.gcp_project_id:
                    from .gcp_scanner import scan_gcp
                    self._emit(scan_id, 80, "Scanning GCP…")
                    servers += scan_gcp(target, progress_cb=lambda p, m: cb(80 + p // 5, m))

                self._emit(scan_id, 96, f"All providers scanned — {len(servers)} servers found")

            else:
                raise ValueError(f"Unknown provider: {provider!r}")

            # Build report
            self._emit(scan_id, 98, "Building report…")
            with self._lock:
                job_ref = self._jobs[scan_id]
            report = build_report(
                servers=servers,
                target=target,
                report_name=job.report_name,
                scan_job=job_ref,
            )

            # Persist report to disk
            report_path = self._reports_dir / f"{scan_id}.json"
            with open(report_path, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=2, default=str)

            with self._lock:
                j = self._jobs[scan_id]
                j.servers = servers
                j.status = "completed"
                j.progress = 100
                j.progress_message = f"Scan complete — {len(servers)} servers discovered"
                j.completed_at = datetime.utcnow().isoformat()

            self._emit(scan_id, 100,
                       f"Scan complete — {len(servers)} servers discovered")

        except Exception as exc:
            log.exception("Scan %s failed", scan_id)
            self._update_job(
                scan_id,
                status="failed",
                error=str(exc),
                progress_message=f"Scan failed: {exc}",
                completed_at=datetime.utcnow().isoformat(),
            )
            self._emit(scan_id, 0, f"ERROR: {exc}")
        finally:
            # Clean up subscribers
            with self._lock:
                self._subscribers.pop(scan_id, None)
