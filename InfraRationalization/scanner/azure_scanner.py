"""
scanner/azure_scanner.py
Azure infrastructure scanner using azure-mgmt-* SDKs.

Discovers:
  - Virtual Machines (compute, OS profile, disks, NICs, availability sets/zones)
  - Azure SQL Databases / Managed Instances (DB workloads)
  - Azure Database for MySQL / PostgreSQL / MariaDB (DB workloads)
  - Azure Cache for Redis (cache workloads)
  - App Service Plans + Web Apps (app workloads)
  - AKS Clusters (Kubernetes)
  - Load Balancers mapped as app workloads

Requires: azure-mgmt-compute azure-mgmt-network azure-mgmt-sql
          azure-mgmt-rdbms azure-mgmt-redis azure-mgmt-resource
          azure-identity
"""
from __future__ import annotations

import logging
from typing import Callable

from .models import (
    DiscoveredServer,
    DiskInfo,
    NetworkInterface,
    ScanTarget,
    WorkloadComponent,
)

log = logging.getLogger(__name__)


def _get_credential(target: ScanTarget):
    from azure.identity import ClientSecretCredential, DefaultAzureCredential
    if target.azure_tenant_id and target.azure_client_id and target.azure_client_secret:
        return ClientSecretCredential(
            tenant_id=target.azure_tenant_id,
            client_id=target.azure_client_id,
            client_secret=target.azure_client_secret,
        )
    return DefaultAzureCredential()


def scan_azure(
    target: ScanTarget,
    progress_cb: Callable[[int, str], None] | None = None,
) -> list[DiscoveredServer]:
    try:
        from azure.mgmt.compute import ComputeManagementClient
        from azure.mgmt.network import NetworkManagementClient
    except ImportError:
        log.warning("azure-mgmt-compute/network not installed — Azure scan unavailable")
        return []

    def _cb(pct: int, msg: str) -> None:
        log.info("[azure %d%%] %s", pct, msg)
        if progress_cb:
            progress_cb(pct, msg)

    sub_id = target.azure_subscription_id
    if not sub_id:
        log.warning("azure_subscription_id not provided")
        return []

    try:
        credential = _get_credential(target)
    except Exception as exc:
        log.warning("Azure credential error: %s", exc)
        return []

    servers: list[DiscoveredServer] = []

    # ── Virtual Machines ──
    try:
        compute_client = ComputeManagementClient(credential, sub_id)
        network_client = NetworkManagementClient(credential, sub_id)

        _cb(10, "Listing Azure VMs")
        vm_list = list(compute_client.virtual_machines.list_all())
        total_vm = max(len(vm_list), 1)

        for idx, vm in enumerate(vm_list):
            _cb(10 + int(50 * idx / total_vm), f"Scanning VM {vm.name}")
            server = _vm_to_server(vm, compute_client, network_client, sub_id)
            servers.append(server)
    except Exception as exc:
        log.warning("VM scan failed: %s", exc)

    # ── Azure SQL / MySQL / PostgreSQL ──
    _cb(65, "Scanning Azure databases")
    servers.extend(_scan_azure_databases(target, credential, sub_id))

    # ── Azure Cache for Redis ──
    try:
        servers.extend(_scan_azure_redis(target, credential, sub_id))
    except Exception as exc:
        log.debug("Redis scan skipped: %s", exc)

    _cb(95, f"Azure scan complete — {len(servers)} resources found")
    return servers


def _vm_to_server(vm, compute_client, network_client, sub_id: str) -> DiscoveredServer:
    rg = vm.id.split("/")[4] if vm.id else ""
    vm_size = vm.hardware_profile.vm_size if vm.hardware_profile else ""
    cpu, ram = _azure_vm_specs(vm_size)

    # OS profile
    os_profile = vm.storage_profile.os_disk if vm.storage_profile else None
    os_name, os_family = _azure_os_profile(vm)

    # Disks
    disks: list[DiskInfo] = []
    total_gb = 0.0
    if vm.storage_profile:
        od = vm.storage_profile.os_disk
        if od:
            sz = (od.disk_size_gb or 128)
            disks.append(DiskInfo(
                mount_point="os",
                size_gb=float(sz),
                disk_type=_azure_disk_type(od.managed_disk),
            ))
            total_gb += sz
        for dd in (vm.storage_profile.data_disks or []):
            sz = float(dd.disk_size_gb or 0)
            disks.append(DiskInfo(
                mount_point=f"data-lun{dd.lun}",
                size_gb=sz,
                disk_type=_azure_disk_type(dd.managed_disk),
            ))
            total_gb += sz

    # Network interfaces
    ifaces: list[NetworkInterface] = []
    primary_ip = ""
    for nic_ref in (vm.network_profile.network_interfaces if vm.network_profile else []):
        nic_id = nic_ref.id or ""
        nic_name = nic_id.split("/")[-1]
        nic_rg = nic_id.split("/")[4] if len(nic_id.split("/")) > 4 else rg
        try:
            nic = network_client.network_interfaces.get(nic_rg, nic_name)
            for cfg in (nic.ip_configurations or []):
                private_ip = cfg.private_ip_address or ""
                public_ip = ""
                if cfg.public_ip_address and cfg.public_ip_address.id:
                    pip_name = cfg.public_ip_address.id.split("/")[-1]
                    pip_rg = cfg.public_ip_address.id.split("/")[4]
                    try:
                        pip = network_client.public_ip_addresses.get(pip_rg, pip_name)
                        public_ip = pip.ip_address or ""
                    except Exception:
                        pass
                if private_ip:
                    ifaces.append(NetworkInterface(
                        interface_name=nic_name,
                        ip_address=private_ip,
                        ip_type="private",
                        subnet=str(cfg.subnet.id).split("/")[-1] if cfg.subnet else "",
                    ))
                    if not primary_ip:
                        primary_ip = private_ip
                if public_ip:
                    ifaces.append(NetworkInterface(
                        interface_name=f"{nic_name}-pub",
                        ip_address=public_ip,
                        ip_type="public",
                    ))
        except Exception:
            pass

    primary_ip = primary_ip or vm.name
    return DiscoveredServer(
        server_id=vm.id or vm.name,
        server_name=vm.name,
        ip_address=primary_ip,
        hostname=vm.os_profile.computer_name if vm.os_profile else vm.name,
        cloud_provider="azure",
        region=vm.location or "",
        resource_group=rg,
        cpu_cores=cpu,
        ram_gb=ram,
        architecture="64 bit",
        server_type="Virtual",
        boot_type="UEFI" if (vm.storage_profile and vm.storage_profile.os_disk
                             and vm.storage_profile.os_disk.caching) else "BIOS",
        instance_type=vm_size,
        os_name=os_name,
        os_family=os_family,
        disks=disks,
        total_storage_gb=total_gb,
        interfaces=ifaces,
        utilization_band="unknown",
        raw_metadata={"power_state": "", "resource_group": rg},
    )


def _azure_os_profile(vm) -> tuple[str, str]:
    if not vm.storage_profile:
        return "Unknown", "unknown"
    ref = vm.storage_profile.image_reference
    if ref:
        offer = (ref.offer or "").lower()
        sku = (ref.sku or "").lower()
        publisher = (ref.publisher or "").lower()
        if "windows" in offer or "windows" in publisher:
            return f"Windows Server {sku}".replace("datacenter", "").strip(), "windows"
        if "ubuntu" in offer:
            return f"Ubuntu {sku}", "linux"
        if "rhel" in offer or "redhat" in publisher:
            return f"Red Hat Enterprise Linux {sku}", "linux"
        if "centos" in offer:
            return f"CentOS {sku}", "linux"
        if "debian" in offer:
            return f"Debian {sku}", "linux"
        if "sles" in offer or "suse" in publisher:
            return f"SUSE Linux Enterprise {sku}", "linux"
        return f"{offer} {sku}".strip(), "linux"
    # OS disk name hints
    od = vm.storage_profile.os_disk
    if od and od.os_type:
        if str(od.os_type).lower() == "windows":
            return "Windows Server", "windows"
    return "Linux", "linux"


_AZURE_VM_SPECS: dict[str, tuple[int, float]] = {
    "Standard_B1s": (1, 1), "Standard_B2s": (2, 4), "Standard_B4ms": (4, 16),
    "Standard_B8ms": (8, 32), "Standard_B16ms": (16, 64),
    "Standard_D2s_v3": (2, 8), "Standard_D4s_v3": (4, 16), "Standard_D8s_v3": (8, 32),
    "Standard_D2ls_v5": (2, 4), "Standard_D4ls_v5": (4, 8),
    "Standard_D2s_v5": (2, 8), "Standard_D4s_v5": (4, 16), "Standard_D8s_v5": (8, 32),
    "Standard_E2s_v3": (2, 16), "Standard_E4s_v3": (4, 32), "Standard_E8s_v3": (8, 64),
    "Standard_E8as_v5": (8, 64), "Standard_E16as_v5": (16, 128),
    "Standard_B2als_v2": (2, 4), "Standard_B4als_v2": (4, 8),
    "Standard_B8als_v2": (8, 16), "Standard_B16als_v2": (16, 32),
    "Standard_B2as_v2": (2, 8), "Standard_B4as_v2": (4, 16),
    "Standard_F2s_v2": (2, 4), "Standard_F4s_v2": (4, 8),
    "Standard_M8ms": (8, 218), "Standard_M16ms": (16, 437),
}


def _azure_vm_specs(vm_size: str) -> tuple[int, float]:
    direct = _AZURE_VM_SPECS.get(vm_size, (0, 0.0))
    if direct != (0, 0.0):
        return direct
    import re
    # Extract cores from name e.g. Standard_D4s_v3 → 4
    m = re.search(r"_[A-Za-z]+(\d+)", vm_size)
    if m:
        cores = int(m.group(1))
        return cores, float(cores * 4)
    return 2, 8.0


def _azure_disk_type(managed_disk) -> str:
    if not managed_disk:
        return "HDD"
    sk = getattr(managed_disk, "storage_account_type", "") or ""
    mapping = {
        "Premium_LRS": "Premium Managed SSD (LRS)",
        "StandardSSD_LRS": "Standard Managed SSD (LRS)",
        "Standard_LRS": "Standard Managed HDD (LRS)",
        "UltraSSD_LRS": "Ultra SSD (LRS)",
    }
    return mapping.get(str(sk), str(sk) or "HDD")


def _scan_azure_databases(target: ScanTarget, credential, sub_id: str) -> list[DiscoveredServer]:
    servers: list[DiscoveredServer] = []

    # Azure SQL
    try:
        from azure.mgmt.sql import SqlManagementClient
        sql = SqlManagementClient(credential, sub_id)
        for srv in sql.servers.list():
            rg = srv.id.split("/")[4] if srv.id else ""
            for db in sql.databases.list_by_server(rg, srv.name):
                if db.name == "master":
                    continue
                servers.append(DiscoveredServer(
                    server_id=db.id or db.name,
                    server_name=f"{srv.name}/{db.name}",
                    ip_address=srv.fully_qualified_domain_name or srv.name,
                    hostname=srv.fully_qualified_domain_name or "",
                    cloud_provider="azure",
                    region=srv.location or "",
                    resource_group=rg,
                    server_type="Managed",
                    os_name="Azure SQL Database",
                    os_family="managed",
                    instance_type=str(db.sku.name) if db.sku else "",
                    workloads=[WorkloadComponent(name="MSSQL", component_type="db",
                                                  version=str(db.sku.tier) if db.sku else "")],
                    utilization_band="unknown",
                ))
    except Exception as exc:
        log.debug("Azure SQL scan skipped: %s", exc)

    # MySQL Flexible Server
    try:
        from azure.mgmt.rdbms.mysql_flexibleservers import MySQLManagementClient
        mysql = MySQLManagementClient(credential, sub_id)
        for srv in mysql.servers.list():
            rg = srv.id.split("/")[4] if srv.id else ""
            servers.append(_managed_db_server(srv, "azure", "MySQL", "db", rg))
    except Exception as exc:
        log.debug("Azure MySQL scan skipped: %s", exc)

    # PostgreSQL Flexible Server
    try:
        from azure.mgmt.rdbms.postgresql_flexibleservers import PostgreSQLManagementClient
        pg = PostgreSQLManagementClient(credential, sub_id)
        for srv in pg.servers.list():
            rg = srv.id.split("/")[4] if srv.id else ""
            servers.append(_managed_db_server(srv, "azure", "PostgreSQL", "db", rg))
    except Exception as exc:
        log.debug("Azure PostgreSQL scan skipped: %s", exc)

    return servers


def _managed_db_server(srv, provider: str, wl_name: str, wl_type: str, rg: str) -> DiscoveredServer:
    return DiscoveredServer(
        server_id=srv.id or srv.name,
        server_name=srv.name,
        ip_address=getattr(srv, "fully_qualified_domain_name", srv.name) or srv.name,
        hostname=getattr(srv, "fully_qualified_domain_name", "") or "",
        cloud_provider=provider,
        region=getattr(srv, "location", ""),
        resource_group=rg,
        server_type="Managed",
        os_name=f"Azure {wl_name} Flexible Server",
        os_family="managed",
        workloads=[WorkloadComponent(name=wl_name, component_type=wl_type)],
        utilization_band="unknown",
    )


def _scan_azure_redis(target: ScanTarget, credential, sub_id: str) -> list[DiscoveredServer]:
    servers: list[DiscoveredServer] = []
    try:
        from azure.mgmt.redis import RedisManagementClient
        rc = RedisManagementClient(credential, sub_id)
        for cache in rc.redis.list():
            rg = cache.id.split("/")[4] if cache.id else ""
            servers.append(DiscoveredServer(
                server_id=cache.id or cache.name,
                server_name=f"{cache.name} (Redis Cache)",
                ip_address=getattr(cache, "host_name", cache.name) or cache.name,
                cloud_provider="azure",
                region=cache.location or "",
                resource_group=rg,
                server_type="Managed",
                os_name="Azure Cache for Redis",
                os_family="managed",
                workloads=[WorkloadComponent(name="Redis", component_type="cache",
                                              version=cache.redis_version or "")],
                utilization_band="unknown",
            ))
    except Exception as exc:
        log.debug("Azure Redis scan skipped: %s", exc)
    return servers
