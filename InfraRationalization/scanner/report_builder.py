"""
scanner/report_builder.py
Converts a list[DiscoveredServer] into a Corent MaaS™-compatible JSON report dict.

Sections produced:
  1. summary           — total_servers, scan metadata
  2. cloud_assessment  — OS/server-type/IP/utilization/storage distribution
  3. cloud_readiness   — migration strategy counts
  4. capacity_planning — equivalence vs best-match totals
  5. vm_flavors        — placeholder flavor recommendations
  6. workload_consolidation — MySQL / Tomcat consolidation hints
  7. paas_recommendations  — managed-service candidates
  8. eos_advisory_os       — OS end-of-support data
  9. eos_advisory_workload — workload end-of-support data
 10. storage_recommendation
 11. kubernetes_recommendation
 12. sustainability         — CO₂/power estimates
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .models import DiscoveredServer, ScanTarget, ScanJob

# ── EOS reference tables ────────────────────────────────────────────────────

_OS_EOS: dict[str, tuple[str, str | None]] = {
    # (end_of_support, extended_support)
    "windows server 2003": ("2015-07-14", None),
    "windows server 2008": ("2020-01-14", "2023-01-10"),
    "windows server 2012": ("2023-10-10", "2026-10-13"),
    "windows server 2016": ("2027-01-12", None),
    "windows server 2019": ("2029-01-09", None),
    "windows server 2022": ("2031-10-14", None),
    "red hat enterprise linux 6": ("2020-11-30", None),
    "red hat enterprise linux 7": ("2024-06-30", None),
    "red hat enterprise linux 8": ("2029-05-31", None),
    "red hat enterprise linux 9": ("2032-05-31", None),
    "centos 6": ("2020-11-30", None),
    "centos 7": ("2024-06-30", None),
    "centos 8": ("2021-12-31", None),
    "ubuntu 16.04": ("2021-04-30", None),
    "ubuntu 18.04": ("2023-04-30", "2028-04-30"),
    "ubuntu 20.04": ("2025-04-30", "2030-04-30"),
    "ubuntu 22.04": ("2027-04-30", "2032-04-30"),
    "debian 9": ("2022-06-30", None),
    "debian 10": ("2024-06-30", None),
    "debian 11": ("2026-06-30", None),
}

_WORKLOAD_EOS: dict[str, str] = {
    # workload_name_lower: end_of_support date
    "mysql 5.5": "2018-12-31",
    "mysql 5.6": "2021-02-28",
    "mysql 5.7": "2023-10-31",
    "mysql 8.0": "2026-04-30",
    "postgresql 9.6": "2021-11-11",
    "postgresql 10": "2022-11-10",
    "postgresql 11": "2023-11-09",
    "postgresql 12": "2024-11-14",
    "postgresql 13": "2025-11-13",
    "postgresql 14": "2026-11-12",
    "postgresql 15": "2027-11-11",
    "mssql server 2014": "2024-07-09",
    "mssql server 2016": "2026-07-14",
    "mssql server 2019": "2030-01-08",
    "apache tomcat 7": "2021-03-31",
    "apache tomcat 8.5": "2024-03-31",
    "apache tomcat 9": "2026-12-31",
    "apache tomcat 10": "2028-12-31",
    "node.js 14": "2023-04-30",
    "node.js 16": "2024-09-11",
    "node.js 18": "2025-04-30",
    "node.js 20": "2026-04-30",
}


def build_report(
    servers: list[DiscoveredServer],
    target: ScanTarget,
    report_name: str,
    scan_job: ScanJob | None = None,
) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    report: dict[str, Any] = {
        "report_name": report_name,
        "generated_at": now,
        "provider": target.provider,
        "scan_id": scan_job.scan_id if scan_job else "",
        "sections": {},
    }

    secs = report["sections"]

    # Run analysis
    secs["summary"] = _build_summary(servers, target)
    secs["cloud_assessment"] = _build_cloud_assessment(servers)
    secs["cloud_readiness"] = _build_cloud_readiness(servers)
    secs["capacity_planning"] = _build_capacity_planning(servers)
    secs["vm_flavors"] = _build_vm_flavors(servers)
    secs["workload_consolidation"] = _build_workload_consolidation(servers)
    secs["paas_recommendations"] = _build_paas_recommendations(servers)
    secs["eos_advisory_os"] = _build_eos_os(servers)
    secs["eos_advisory_workload"] = _build_eos_workload(servers)
    secs["storage_recommendation"] = _build_storage_recommendation(servers)
    secs["kubernetes_recommendation"] = _build_kubernetes_recommendation(servers)
    secs["sustainability"] = _build_sustainability(servers)

    # Include raw server list for detail view
    report["servers"] = [_server_to_dict(s) for s in servers]

    return report


# ── Section builders ────────────────────────────────────────────────────────

def _build_summary(servers: list[DiscoveredServer], target: ScanTarget) -> dict:
    return {
        "total_servers": len(servers),
        "provider": target.provider,
        "scan_target": target.network_range or target.gcp_project_id or target.azure_subscription_id or "",
        "cloud_providers": list({s.cloud_provider for s in servers if s.cloud_provider}),
        "regions": list({s.region for s in servers if s.region}),
    }


def _build_cloud_assessment(servers: list[DiscoveredServer]) -> dict:
    os_dist: dict[str, int] = defaultdict(int)
    util_dist: dict[str, int] = defaultdict(int)
    server_type_dist: dict[str, int] = defaultdict(int)
    boot_type_dist: dict[str, int] = defaultdict(int)
    ip_dist: dict[str, int] = defaultdict(int)
    total_storage_tb = 0.0
    total_ram_gb = 0.0
    total_cpu = 0

    for s in servers:
        os_key = s.os_family or "unknown"
        if "windows" in (s.os_name or "").lower():
            os_key = "Windows"
        elif "linux" in (s.os_name or "").lower() or os_key == "linux":
            os_key = "Linux"
        elif os_key == "managed":
            os_key = "Managed Service"
        os_dist[os_key] += 1

        util_dist[s.utilization_band or "unknown"] += 1
        server_type_dist[s.server_type or "Virtual"] += 1
        boot_type_dist[s.boot_type or "BIOS"] += 1

        for iface in s.interfaces:
            ip_dist[iface.ip_type or "private"] += 1

        total_storage_tb += (s.total_storage_gb or 0) / 1024
        total_ram_gb += s.ram_gb or 0
        total_cpu += s.cpu_cores or 0

    return {
        "total_servers": len(servers),
        "os_distribution": dict(os_dist),
        "utilization_distribution": dict(util_dist),
        "server_type_distribution": dict(server_type_dist),
        "boot_type_distribution": dict(boot_type_dist),
        "ip_type_distribution": dict(ip_dist),
        "total_storage_tb": round(total_storage_tb, 2),
        "total_ram_gb": round(total_ram_gb, 1),
        "total_cpu_cores": total_cpu,
    }


def _assign_migration_strategy(server: DiscoveredServer) -> str:
    """Classify each server: lift_and_shift / smart_shift / paas / decommission."""
    os_lower = (server.os_name or "").lower()
    wl_types = {w.component_type for w in server.workloads}

    # Already a managed service → PaaS
    if server.server_type == "Managed" or server.os_family == "managed":
        return "paas"

    # End-of-life OS → replatform advice
    eos = _os_eos_date(server.os_name or "")
    if eos and eos < date.today():
        return "smart_shift"

    # Stateless webapp tier → PaaS candidate
    if "web" in wl_types or "app" in wl_types:
        if not ("db" in wl_types):
            return "paas"

    # Heavy database workloads → smart shift (containerise/managed DB)
    if "db" in wl_types and len(server.workloads) >= 1:
        return "smart_shift"

    # Under-utilised Windows → lift-and-shift
    if "windows" in os_lower and server.utilization_band in ("underutilized", "unknown"):
        return "lift_and_shift"

    # Default: lift-and-shift
    return "lift_and_shift"


def _build_cloud_readiness(servers: list[DiscoveredServer]) -> dict:
    strategy_counts: dict[str, int] = defaultdict(int)
    cloud_ready_count = 0
    not_ready_count = 0
    details = []

    for s in servers:
        strat = _assign_migration_strategy(s)
        strategy_counts[strat] += 1
        ready = strat in ("lift_and_shift", "smart_shift", "paas")
        if ready:
            cloud_ready_count += 1
        else:
            not_ready_count += 1
        details.append({
            "server_name": s.server_name,
            "ip": s.ip_address,
            "os": s.os_name,
            "migration_strategy": strat,
            "cloud_ready": ready,
        })

    return {
        "cloud_ready": cloud_ready_count,
        "not_ready": not_ready_count,
        "lift_and_shift": strategy_counts["lift_and_shift"],
        "smart_shift": strategy_counts["smart_shift"],
        "paas_shift": strategy_counts["paas"],
        "total": len(servers),
        "details": details,
    }


def _build_capacity_planning(servers: list[DiscoveredServer]) -> dict:
    """Equivalence match vs best match resource summary."""
    total_cpu = sum(s.cpu_cores or 0 for s in servers)
    total_ram = sum(s.ram_gb or 0.0 for s in servers)
    total_disk_tb = sum((s.total_storage_gb or 0) for s in servers) / 1024

    # Best match: right-size — assume 20% headroom
    best_cpu = max(1, math.ceil(total_cpu * 0.6))
    best_ram = round(total_ram * 0.65, 1)
    physical_count = len([s for s in servers if s.server_type == "Physical"])
    virtual_count = len(servers) - physical_count

    return {
        "equivalence_match": {
            "total_servers": len(servers),
            "virtual_servers": virtual_count,
            "physical_servers": physical_count,
            "total_cpu_cores": total_cpu,
            "total_ram_gb": round(total_ram, 1),
            "total_disk_tb": round(total_disk_tb, 2),
        },
        "best_match": {
            "total_servers": max(1, math.ceil(len(servers) * 0.65)),
            "total_cpu_cores": best_cpu,
            "total_ram_gb": best_ram,
            "total_disk_tb": round(total_disk_tb * 0.7, 2),
            "estimated_saving_pct": 30,
        },
    }


def _build_vm_flavors(servers: list[DiscoveredServer]) -> dict:
    """Group discovered servers by instance type / size profile."""
    flavor_map: dict[str, list[str]] = defaultdict(list)
    for s in servers:
        key = s.instance_type or _autosize_flavor(s.cpu_cores or 2, s.ram_gb or 8)
        flavor_map[key].append(s.server_name)

    flavors = []
    for flavor, names in flavor_map.items():
        flavors.append({
            "flavor": flavor,
            "count": len(names),
            "servers": names[:5],  # preview only
        })

    return {"flavors": sorted(flavors, key=lambda x: -x["count"])}


def _autosize_flavor(cpu: int, ram: float) -> str:
    if cpu <= 2 and ram <= 8:
        return "Small (2vCPU / 8GB)"
    if cpu <= 4 and ram <= 16:
        return "Medium (4vCPU / 16GB)"
    if cpu <= 8 and ram <= 32:
        return "Large (8vCPU / 32GB)"
    return f"Custom ({cpu}vCPU / {ram}GB)"


def _build_workload_consolidation(servers: list[DiscoveredServer]) -> list[dict]:
    """Identify workloads that run on many VMs and could be consolidated."""
    workload_servers: dict[str, list[str]] = defaultdict(list)
    for s in servers:
        for w in s.workloads:
            workload_servers[w.name].append(s.server_name)

    results = []
    for wl_name, sve in workload_servers.items():
        if len(sve) >= 2:  # consolidation candidate
            results.append({
                "workload": wl_name,
                "current_vm_count": len(sve),
                "recommended_vm_count": max(1, math.ceil(len(sve) * 0.4)),
                "servers": sve,
                "recommendation": (
                    f"Consolidate {len(sve)} {wl_name} instances down to "
                    f"{max(1, math.ceil(len(sve) * 0.4))} VM(s) using clustering / containers."
                ),
            })
    return sorted(results, key=lambda x: -x["current_vm_count"])


def _build_paas_recommendations(servers: list[DiscoveredServer]) -> list[dict]:
    """Servers with managed-service workloads that are PaaS candidates."""
    recs = []
    for s in servers:
        for w in s.workloads:
            paas_map = {
                "MySQL": "AWS RDS MySQL / Azure Database for MySQL / Cloud SQL",
                "PostgreSQL": "AWS RDS PostgreSQL / Azure Database for PostgreSQL / Cloud SQL",
                "MSSQL": "AWS RDS SQL Server / Azure SQL Database",
                "Oracle": "AWS RDS Oracle / Oracle Autonomous Database",
                "MongoDB": "MongoDB Atlas / Azure Cosmos DB",
                "Redis": "AWS ElastiCache / Azure Cache for Redis / Memorystore",
                "Memcached": "AWS ElastiCache / Azure Cache for Redis",
                "RabbitMQ": "AWS Amazon MQ / Azure Service Bus",
                "Kafka": "AWS MSK / Azure Event Hubs / Confluent Cloud",
            }
            if w.name in paas_map:
                recs.append({
                    "server": s.server_name,
                    "ip": s.ip_address,
                    "workload": w.name,
                    "version": w.version or "",
                    "paas_target": paas_map[w.name],
                    "benefit": "No server management, automated backups, HA, auto-scaling",
                })
    return recs


def _os_eos_date(os_name: str) -> date | None:
    os_lower = os_name.lower()
    for key, (eos, _ext) in _OS_EOS.items():
        if key in os_lower:
            return date.fromisoformat(eos)
    return None


def _build_eos_os(servers: list[DiscoveredServer]) -> list[dict]:
    rows = []
    today = date.today()
    for s in servers:
        os_lower = (s.os_name or "").lower()
        for key, (eos, ext) in _OS_EOS.items():
            if key in os_lower:
                eos_date = date.fromisoformat(eos)
                rows.append({
                    "server_name": s.server_name,
                    "ip_address": s.ip_address,
                    "os_name": s.os_name,
                    "end_of_support": eos,
                    "extended_support": ext,
                    "is_eos": eos_date < today,
                    "days_to_eos": (eos_date - today).days,
                    "migration_advisory": (
                        f"Migrate from {s.os_name} to a supported OS version immediately."
                        if eos_date < today else
                        f"Plan migration before {eos} end-of-support date."
                    ),
                })
                break
    return sorted(rows, key=lambda x: x["end_of_support"])


def _build_eos_workload(servers: list[DiscoveredServer]) -> list[dict]:
    rows = []
    today = date.today()
    for s in servers:
        for w in s.workloads:
            key = f"{w.name.lower()} {(w.version or '').lower()}".strip()
            eos = None
            for eos_key, eos_date in _WORKLOAD_EOS.items():
                if key == eos_key or (w.name.lower() in eos_key and
                                       (w.version or "").lower() in eos_key):
                    eos = eos_date
                    break
            if eos:
                eos_d = date.fromisoformat(eos)
                rows.append({
                    "server_name": s.server_name,
                    "ip_address": s.ip_address,
                    "workload": w.name,
                    "version": w.version or "",
                    "end_of_support": eos,
                    "is_eos": eos_d < today,
                    "days_to_eos": (eos_d - today).days,
                    "migration_advisory": (
                        f"Upgrade {w.name} {w.version} — EOS reached {eos}."
                        if eos_d < today else
                        f"Plan {w.name} upgrade before {eos}."
                    ),
                })
    return sorted(rows, key=lambda x: x["end_of_support"])


def _build_storage_recommendation(servers: list[DiscoveredServer]) -> dict:
    total_tb = sum((s.total_storage_gb or 0) for s in servers) / 1024
    hdd_tb = 0.0
    ssd_tb = 0.0
    for s in servers:
        for d in s.disks:
            gb = d.size_gb or 0
            if "ssd" in (d.disk_type or "").lower() or "nvme" in (d.disk_type or "").lower():
                ssd_tb += gb / 1024
            else:
                hdd_tb += gb / 1024

    return {
        "total_storage_tb": round(total_tb, 2),
        "hdd_storage_tb": round(hdd_tb, 2),
        "ssd_storage_tb": round(ssd_tb, 2),
        "recommendations": [
            {"type": "Object Storage", "target": "AWS S3 / Azure Blob / GCS",
             "applicable_tb": round(hdd_tb * 0.4, 2),
             "notes": "Cold/archival data — significant cost reduction"},
            {"type": "Block Storage", "target": "AWS EBS gp3 / Azure Premium SSD",
             "applicable_tb": round(ssd_tb, 2),
             "notes": "Hot workloads requiring low-latency IOPS"},
            {"type": "File Storage", "target": "AWS EFS / Azure Files / Filestore",
             "applicable_tb": round(hdd_tb * 0.2, 2),
             "notes": "Shared file systems and home directories"},
        ],
    }


def _build_kubernetes_recommendation(servers: list[DiscoveredServer]) -> dict:
    """Identify containerization candidates (stateless apps)."""
    candidates = []
    for s in servers:
        for w in s.workloads:
            if w.component_type in ("web", "app", "middleware"):
                candidates.append({
                    "server": s.server_name,
                    "workload": w.name,
                    "workload_type": w.component_type,
                    "recommended_pods": 2,
                    "cpu_request": f"{max(0.5, (s.cpu_cores or 2) * 0.25)}",
                    "memory_request": f"{max(512, int((s.ram_gb or 4) * 256))}Mi",
                })

    total_cpu = sum(float(c["cpu_request"]) for c in candidates)
    total_mem_mi = sum(int(c["memory_request"].rstrip("Mi")) for c in candidates)

    cluster_nodes = max(1, math.ceil(len(candidates) / 10))

    return {
        "containerization_candidates": len(candidates),
        "candidates": candidates,
        "recommended_cluster": {
            "node_count": cluster_nodes,
            "node_type": "4vCPU / 16GB",
            "total_cpu_request": round(total_cpu, 1),
            "total_memory_request_mi": total_mem_mi,
        } if candidates else None,
    }


def _build_sustainability(servers: list[DiscoveredServer]) -> dict:
    """Estimate current vs cloud power consumption and CO₂ reduction."""
    # Rough estimate: physical server ~300W, VM ~150W, managed ~50W
    current_watts = 0
    for s in servers:
        if s.server_type == "Physical":
            current_watts += 300
        elif s.server_type == "Managed":
            current_watts += 50
        else:
            current_watts += 150

    cloud_watts = current_watts * 0.4  # cloud typically ~60% more efficient
    saving_kwh_year = (current_watts - cloud_watts) * 8760 / 1000
    # ~0.4 kg CO₂ per kWh (global average)
    co2_saving_kg = saving_kwh_year * 0.4

    return {
        "current_power_w": current_watts,
        "cloud_equivalent_power_w": int(cloud_watts),
        "annual_power_saving_kwh": round(saving_kwh_year, 0),
        "annual_co2_saving_kg": round(co2_saving_kg, 0),
        "annual_co2_saving_tonnes": round(co2_saving_kg / 1000, 2),
        "notes": "Estimates based on industry average PUE ratios and server power profiles.",
    }


# ── Serialise DiscoveredServer to plain dict ─────────────────────────────────

def _server_to_dict(s: DiscoveredServer) -> dict:
    return {
        "server_id": s.server_id,
        "server_name": s.server_name,
        "ip_address": s.ip_address,
        "hostname": s.hostname,
        "cloud_provider": s.cloud_provider,
        "region": s.region,
        "resource_group": s.resource_group,
        "cpu_cores": s.cpu_cores,
        "ram_gb": s.ram_gb,
        "architecture": s.architecture,
        "server_type": s.server_type,
        "boot_type": s.boot_type,
        "instance_type": s.instance_type,
        "os_name": s.os_name,
        "os_family": s.os_family,
        "os_version": s.os_version,
        "total_storage_gb": s.total_storage_gb,
        "disks": [{"mount_point": d.mount_point, "size_gb": d.size_gb,
                   "used_gb": d.used_gb, "disk_type": d.disk_type, "iops": d.iops}
                  for d in s.disks],
        "interfaces": [{"interface_name": i.interface_name, "ip_address": i.ip_address,
                        "ip_type": i.ip_type, "mac_address": i.mac_address,
                        "subnet": i.subnet, "bandwidth_mbps": i.bandwidth_mbps}
                       for i in s.interfaces],
        "cpu_util_pct": s.cpu_util_pct,
        "ram_util_pct": s.ram_util_pct,
        "utilization_band": s.utilization_band,
        "workloads": [{"name": w.name, "version": w.version,
                       "component_type": w.component_type, "port": w.port,
                       "status": w.status}
                      for w in s.workloads],
        "migration_strategy": s.migration_strategy,
        "cloud_ready": s.cloud_ready,
    }
