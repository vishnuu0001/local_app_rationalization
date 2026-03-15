"""
scanner/models.py
Shared dataclasses that every provider populates.
The ScanJob is what goes into the report_builder and then gets persisted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ─── Per-server model ──────────────────────────────────────────────────────────

@dataclass
class DiskInfo:
    mount_point: str = ""
    size_gb: float = 0.0
    used_gb: float = 0.0
    disk_type: str = "unknown"        # SSD / HDD / NVMe / network
    iops: int = 0


@dataclass
class NetworkInterface:
    interface_name: str = ""
    ip_address: str = ""
    ip_type: str = "private"          # private / public / elastic / ISP
    mac_address: str = ""
    subnet: str = ""
    bandwidth_mbps: int = 0


@dataclass
class WorkloadComponent:
    name: str = ""                    # e.g. MySQL, ApacheTomcat, nginx, PostgreSQL
    version: str = ""
    component_type: str = ""          # db / web / app / cache / queue / ldap / mail
    port: int = 0
    status: str = "running"


@dataclass
class DiscoveredServer:
    # Identity
    server_id: str = ""
    server_name: str = ""
    ip_address: str = ""
    hostname: str = ""
    cloud_provider: str = ""          # onprem / aws / azure / gcp
    region: str = ""
    resource_group: str = ""          # Azure RG / AWS VPC / GCP project

    # Compute
    cpu_cores: int = 0
    ram_gb: float = 0.0
    architecture: str = "64 bit"
    server_type: str = "Virtual"      # Physical / Virtual
    boot_type: str = "BIOS"           # BIOS / UEFI
    instance_type: str = ""           # e.g. t3.medium, Standard_D2s_v3

    # OS
    os_name: str = ""                 # e.g. Ubuntu 24.04 LTS
    os_family: str = ""               # linux / windows
    os_version: str = ""
    os_end_of_support: str = ""       # ISO date or empty
    os_extended_support: str = ""
    os_migration_advisory: str = ""

    # Storage
    disks: list[DiskInfo] = field(default_factory=list)
    total_storage_gb: float = 0.0

    # Network
    interfaces: list[NetworkInterface] = field(default_factory=list)

    # Utilization (0..100 percentages; -1 = unknown)
    cpu_util_pct: float = -1.0
    ram_util_pct: float = -1.0
    disk_util_pct: float = -1.0
    utilization_band: str = "unknown"   # underutilized / moderate / utilized

    # Workloads running on this server
    workloads: list[WorkloadComponent] = field(default_factory=list)

    # Cloud migration fields (populated by report_builder)
    migration_strategy: str = ""        # lift_and_shift / smart_shift / paas_shift
    cloud_ready: bool = True

    # Raw provider metadata
    raw_metadata: dict[str, Any] = field(default_factory=dict)


# ─── Scan job (aggregation of all discovered servers) ─────────────────────────

@dataclass
class ScanTarget:
    provider: str = "onprem"            # onprem / aws / azure / gcp
    # OnPrem
    network_range: str = ""             # e.g. 192.168.1.0/24
    ssh_username: str = ""
    ssh_password: str = ""
    ssh_key_path: str = ""
    winrm_username: str = ""
    winrm_password: str = ""
    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_regions: list[str] = field(default_factory=list)
    # Azure
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_subscription_id: str = ""
    azure_regions: list[str] = field(default_factory=list)
    # GCP
    gcp_project_id: str = ""
    gcp_service_account_json: str = ""  # JSON key string
    gcp_regions: list[str] = field(default_factory=list)
    # Scan options
    deep_scan: bool = True              # attempt SSH/WMI/SDK for full details
    port_scan: bool = True              # nmap port scan
    timeout_seconds: int = 120


@dataclass
class ScanJob:
    scan_id: str = ""
    report_name: str = ""
    target: ScanTarget = field(default_factory=ScanTarget)
    status: str = "pending"             # pending / running / completed / failed
    progress: int = 0                   # 0..100
    progress_message: str = ""
    error: str = ""
    servers: list[DiscoveredServer] = field(default_factory=list)
    created_at: str = ""
    completed_at: str = ""
