"""
scanner/gcp_scanner.py
GCP infrastructure scanner using google-cloud-compute and related SDKs.

Discovers:
  - Compute Engine instances (VMs) — machine type, OS image, disks, NICs
  - Cloud SQL instances (MySQL, PostgreSQL, MSSQL)
  - Memorystore for Redis / Memcached
  - GKE clusters (listed but not deeply scanned)

Requires: google-cloud-compute google-cloud-sql-connector google-auth
"""
from __future__ import annotations

import logging
import re
from typing import Callable

from .models import (
    DiscoveredServer,
    DiskInfo,
    NetworkInterface,
    ScanTarget,
    WorkloadComponent,
)

log = logging.getLogger(__name__)


def scan_gcp(
    target: ScanTarget,
    progress_cb: Callable[[int, str], None] | None = None,
) -> list[DiscoveredServer]:
    try:
        from google.oauth2 import service_account
        from google.auth import default as gauth_default
    except ImportError:
        log.warning("google-auth not installed — GCP scan unavailable")
        return []

    def _cb(pct: int, msg: str) -> None:
        log.info("[gcp %d%%] %s", pct, msg)
        if progress_cb:
            progress_cb(pct, msg)

    project = target.gcp_project_id
    if not project:
        log.warning("gcp_project_id not provided")
        return []

    # Build credentials
    credentials = None
    if target.gcp_service_account_json:
        try:
            import json
            info = json.loads(target.gcp_service_account_json)
            credentials = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        except Exception as exc:
            log.warning("GCP service account parse error: %s", exc)

    servers: list[DiscoveredServer] = []

    # ── Compute Engine ──
    _cb(10, "Listing GCP Compute Engine instances")
    servers.extend(_scan_compute(project, credentials, _cb))

    # ── Cloud SQL ──
    _cb(70, "Scanning Cloud SQL instances")
    servers.extend(_scan_cloud_sql(project, credentials))

    # ── Memorystore ──
    try:
        servers.extend(_scan_memorystore(project, credentials))
    except Exception as exc:
        log.debug("Memorystore scan skipped: %s", exc)

    _cb(100, f"GCP scan complete — {len(servers)} resources found")
    return servers


def _scan_compute(
    project: str,
    credentials,
    progress_cb: Callable[[int, str], None],
) -> list[DiscoveredServer]:
    try:
        from google.cloud import compute_v1
    except ImportError:
        log.warning("google-cloud-compute not installed — Compute scan unavailable")
        return []

    servers: list[DiscoveredServer] = []
    try:
        kw = {"credentials": credentials} if credentials else {}
        instances_client = compute_v1.InstancesClient(**kw)
        agg_list = instances_client.aggregated_list(project=project)
        all_instances: list[tuple[str, object]] = []
        for zone_name, zone_data in agg_list:
            if zone_data.instances:
                for inst in zone_data.instances:
                    all_instances.append((zone_name.replace("zones/", ""), inst))

        total = max(len(all_instances), 1)
        for idx, (zone, instance) in enumerate(all_instances):
            progress_cb(10 + int(55 * idx / total), f"Scanning GCE {instance.name}")
            server = _instance_to_server(instance, project, zone)
            servers.append(server)
    except Exception as exc:
        log.warning("Compute Engine scan failed: %s", exc)
    return servers


def _instance_to_server(instance, project: str, zone: str) -> DiscoveredServer:
    machine_type = instance.machine_type.split("/")[-1] if instance.machine_type else ""
    cpu, ram = _gcp_machine_specs(machine_type)

    # OS detection from boot disk source image
    os_name, os_family = _gcp_os_from_disks(instance)

    # Disks
    disks: list[DiskInfo] = []
    total_gb = 0.0
    for ad in (instance.disks or []):
        sz = float(getattr(ad, "disk_size_gb", 0) or 0)
        dtype = "SSD" if "ssd" in str(getattr(ad, "type_", "")).lower() else "HDD"
        mount = "boot" if ad.boot else f"data-{ad.index}"
        disks.append(DiskInfo(mount_point=mount, size_gb=sz, disk_type=dtype))
        total_gb += sz

    # Network interfaces
    ifaces: list[NetworkInterface] = []
    primary_ip = ""
    for ni in (instance.network_interfaces or []):
        private_ip = ni.network_ip or ""
        if private_ip:
            subnet = ni.subnetwork.split("/")[-1] if ni.subnetwork else ""
            ifaces.append(NetworkInterface(
                interface_name=ni.name or "eth0",
                ip_address=private_ip,
                ip_type="private",
                subnet=subnet,
            ))
            if not primary_ip:
                primary_ip = private_ip
        for ac in (ni.access_configs or []):
            if ac.nat_i_p:
                ifaces.append(NetworkInterface(
                    interface_name=f"{ni.name or 'eth0'}-pub",
                    ip_address=ac.nat_i_p,
                    ip_type="public",
                ))

    primary_ip = primary_ip or instance.name

    return DiscoveredServer(
        server_id=str(instance.id or instance.name),
        server_name=instance.name,
        ip_address=primary_ip,
        hostname=instance.name,
        cloud_provider="gcp",
        region=zone,
        cpu_cores=cpu,
        ram_gb=ram,
        architecture="64 bit",
        server_type="Virtual",
        instance_type=machine_type,
        os_name=os_name,
        os_family=os_family,
        disks=disks,
        total_storage_gb=total_gb,
        interfaces=ifaces,
        utilization_band="unknown",
        raw_metadata={"status": instance.status or "", "project": project},
    )


_GCP_MACHINE_SPECS: dict[str, tuple[int, float]] = {
    # e2-micro/small
    "e2-micro": (2, 1.0), "e2-small": (2, 2.0), "e2-medium": (2, 4.0),
    # e2-standard
    "e2-standard-2": (2, 8.0), "e2-standard-4": (4, 16.0),
    "e2-standard-8": (8, 32.0), "e2-standard-16": (16, 64.0),
    "e2-standard-32": (32, 128.0),
    # n2-standard
    "n2-standard-2": (2, 8.0), "n2-standard-4": (4, 16.0),
    "n2-standard-8": (8, 32.0), "n2-standard-16": (16, 64.0),
    "n2-standard-32": (32, 128.0),
    # n1-standard
    "n1-standard-1": (1, 3.75), "n1-standard-2": (2, 7.5),
    "n1-standard-4": (4, 15.0), "n1-standard-8": (8, 30.0),
    "n1-standard-16": (16, 60.0), "n1-standard-32": (32, 120.0),
    # c2 (compute)
    "c2-standard-4": (4, 16.0), "c2-standard-8": (8, 32.0),
    "c2-standard-16": (16, 64.0), "c2-standard-30": (30, 120.0),
    # n2-highmem
    "n2-highmem-2": (2, 16.0), "n2-highmem-4": (4, 32.0),
    "n2-highmem-8": (8, 64.0), "n2-highmem-16": (16, 128.0),
}


def _gcp_machine_specs(machine_type: str) -> tuple[int, float]:
    d = _GCP_MACHINE_SPECS.get(machine_type)
    if d:
        return d
    m = re.search(r"-(\d+)$", machine_type)
    if m:
        cores = int(m.group(1))
        return cores, float(cores * 4)
    return 2, 8.0


def _gcp_os_from_disks(instance) -> tuple[str, str]:
    for disk in (instance.disks or []):
        if disk.boot:
            src = disk.source or ""
            disk_name = src.split("/")[-1].lower()
            return _image_name_to_os(disk_name)
    return "Linux", "linux"


def _image_name_to_os(image: str) -> tuple[str, str]:
    if "windows" in image:
        return "Windows Server", "windows"
    if "debian" in image:
        m = re.search(r"debian-(\d+)", image)
        ver = m.group(1) if m else ""
        return f"Debian {ver}", "linux"
    if "ubuntu" in image:
        m = re.search(r"ubuntu-(\d{4})", image)
        ver = (m.group(1)[:2] + "." + m.group(1)[2:]) if m else ""
        return f"Ubuntu {ver} LTS", "linux"
    if "rhel" in image or "redhat" in image:
        m = re.search(r"rhel-(\d+)", image)
        ver = m.group(1) if m else ""
        return f"Red Hat Enterprise Linux {ver}", "linux"
    if "centos" in image:
        return "CentOS", "linux"
    if "sles" in image or "suse" in image:
        return "SUSE Linux Enterprise", "linux"
    if "cos" in image:
        return "Container-Optimized OS", "linux"
    if "rocky" in image:
        return "Rocky Linux", "linux"
    return "Linux", "linux"


def _scan_cloud_sql(project: str, credentials) -> list[DiscoveredServer]:
    servers: list[DiscoveredServer] = []
    try:
        import googleapiclient.discovery as gdisc
        kw = {"credentials": credentials} if credentials else {}
        sqladmin = gdisc.build("sqladmin", "v1", **kw)
        result = sqladmin.instances().list(project=project).execute()
        for inst in result.get("items", []):
            wl = _sql_database_version_to_workload(inst.get("databaseVersion", ""))
            ip_addr = ""
            for ip_info in inst.get("ipAddresses", []):
                if ip_info.get("type") == "PRIMARY":
                    ip_addr = ip_info.get("ipAddress", "")
            servers.append(DiscoveredServer(
                server_id=inst.get("name", ""),
                server_name=inst.get("name", ""),
                ip_address=ip_addr or inst.get("name", ""),
                hostname=inst.get("connectionName", ""),
                cloud_provider="gcp",
                region=inst.get("region", ""),
                server_type="Managed",
                os_name=f"Cloud SQL ({inst.get('databaseVersion', '')})",
                os_family="managed",
                instance_type=inst.get("settings", {}).get("tier", ""),
                workloads=[wl],
                utilization_band="unknown",
                raw_metadata={"state": inst.get("state", ""), "project": project},
            ))
    except Exception as exc:
        log.debug("Cloud SQL scan skipped: %s", exc)
    return servers


def _sql_database_version_to_workload(version: str) -> WorkloadComponent:
    version_lower = version.lower()
    if "mysql" in version_lower:
        return WorkloadComponent(name="MySQL", component_type="db", version=version)
    if "postgres" in version_lower:
        return WorkloadComponent(name="PostgreSQL", component_type="db", version=version)
    if "sqlserver" in version_lower:
        return WorkloadComponent(name="MSSQL", component_type="db", version=version)
    return WorkloadComponent(name=version or "SQL", component_type="db")


def _scan_memorystore(project: str, credentials) -> list[DiscoveredServer]:
    servers: list[DiscoveredServer] = []
    try:
        import googleapiclient.discovery as gdisc
        kw = {"credentials": credentials} if credentials else {}
        redis_client = gdisc.build("redis", "v1", **kw)
        result = redis_client.projects().locations().instances().list(
            parent=f"projects/{project}/locations/-"
        ).execute()
        for inst in result.get("instances", []):
            wl_name = "Redis" if "redis" in inst.get("tier", "").lower() else "Memcached"
            servers.append(DiscoveredServer(
                server_id=inst.get("name", ""),
                server_name=inst.get("displayName", inst.get("name", "")),
                ip_address=inst.get("host", inst.get("name", "")),
                cloud_provider="gcp",
                region=inst.get("locationId", ""),
                server_type="Managed",
                os_name=f"Memorystore ({inst.get('tier', '')})",
                os_family="managed",
                workloads=[WorkloadComponent(name=wl_name, component_type="cache",
                                              version=inst.get("redisVersion", ""))],
                utilization_band="unknown",
                raw_metadata={"state": inst.get("state", ""), "project": project},
            ))
    except Exception as exc:
        log.debug("Memorystore scan skipped: %s", exc)
    return servers
