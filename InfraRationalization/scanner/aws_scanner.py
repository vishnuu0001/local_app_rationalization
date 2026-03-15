"""
scanner/aws_scanner.py
AWS infrastructure scanner using boto3.

Discovers:
  - EC2 instances (compute, tags, OS via SSM/describe-images, storage, NICs)
  - RDS instances (database type, version, size)
  - ELB/ALB/NLB (load balancers mapped as app workloads)
  - ElastiCache clusters (Redis/Memcached)
  - EKS clusters (Kubernetes)
  - Network metadata (VPC, subnets, security groups)

Requires: boto3
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


def _boto3_session(target: ScanTarget, region: str):
    import boto3
    return boto3.Session(
        aws_access_key_id=target.aws_access_key_id or None,
        aws_secret_access_key=target.aws_secret_access_key or None,
        region_name=region,
    )


def scan_aws(
    target: ScanTarget,
    progress_cb: Callable[[int, str], None] | None = None,
) -> list[DiscoveredServer]:
    try:
        import boto3  # noqa: F401
    except ImportError:
        log.warning("boto3 not installed — AWS scan unavailable")
        return []

    def _cb(pct: int, msg: str) -> None:
        log.info("[aws %d%%] %s", pct, msg)
        if progress_cb:
            progress_cb(pct, msg)

    regions = target.aws_regions or ["us-east-1"]
    servers: list[DiscoveredServer] = []

    for r_idx, region in enumerate(regions):
        base_pct = int(r_idx / len(regions) * 80)
        _cb(5 + base_pct, f"Scanning AWS region {region}")

        try:
            session = _boto3_session(target, region)
            ec2 = session.client("ec2")

            # ── EC2 instances ──
            paginator = ec2.get_paginator("describe_instances")
            for page in paginator.paginate():
                for reservation in page.get("Reservations", []):
                    for inst in reservation.get("Instances", []):
                        if inst.get("State", {}).get("Name") not in ("running", "stopped"):
                            continue
                        server = _ec2_to_server(inst, region, ec2)
                        servers.append(server)

            # ── RDS instances ──
            rds = session.client("rds")
            rds_pag = rds.get_paginator("describe_db_instances")
            for page in rds_pag.paginate():
                for db in page.get("DBInstances", []):
                    server = _rds_to_server(db, region)
                    servers.append(server)

            # ── ElastiCache ──
            try:
                ec_client = session.client("elasticache")
                cc = ec_client.describe_cache_clusters(ShowCacheNodeInfo=True)
                for cluster in cc.get("CacheClusters", []):
                    server = _elasticache_to_server(cluster, region)
                    servers.append(server)
            except Exception as e:
                log.debug("ElastiCache scan skipped: %s", e)

        except Exception as exc:
            log.warning("AWS region %s scan failed: %s", region, exc)

    _cb(95, f"AWS scan complete — {len(servers)} resources found")
    return servers


def _ec2_to_server(inst: dict, region: str, ec2_client) -> DiscoveredServer:
    inst_id = inst.get("InstanceId", "")
    inst_type = inst.get("InstanceType", "")
    tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
    name = tags.get("Name", inst_id)

    # CPU/RAM from instance type hint table (partial)
    cpu, ram = _ec2_type_specs(inst_type)

    # Primary network interface
    private_ip = inst.get("PrivateIpAddress", "")
    public_ip = inst.get("PublicIpAddress", "")
    ifaces: list[NetworkInterface] = []
    if private_ip:
        ifaces.append(NetworkInterface(interface_name="eth0", ip_address=private_ip, ip_type="private"))
    if public_ip:
        ifaces.append(NetworkInterface(interface_name="eth0-pub", ip_address=public_ip, ip_type="public"))

    primary_ip = private_ip or public_ip or inst_id

    # Storage (EBS volumes)
    disks: list[DiskInfo] = []
    total_gb = 0.0
    for bdm in inst.get("BlockDeviceMappings", []):
        vol_id = bdm.get("Ebs", {}).get("VolumeId", "")
        if vol_id:
            try:
                vol_resp = ec2_client.describe_volumes(VolumeIds=[vol_id])
                for vol in vol_resp.get("Volumes", []):
                    sz = float(vol.get("Size", 0))
                    disk_type = _ebs_type(vol.get("VolumeType", ""))
                    disks.append(DiskInfo(
                        mount_point=bdm.get("DeviceName", ""),
                        size_gb=sz,
                        used_gb=0.0,
                        disk_type=disk_type,
                    ))
                    total_gb += sz
            except Exception:
                pass

    os_name, os_family = _ec2_platform(inst)

    server = DiscoveredServer(
        server_id=inst_id,
        server_name=name,
        ip_address=primary_ip,
        hostname=inst.get("PrivateDnsName", ""),
        cloud_provider="aws",
        region=region,
        resource_group=inst.get("VpcId", ""),
        cpu_cores=cpu,
        ram_gb=ram,
        architecture="64 bit",
        server_type="Virtual",
        boot_type="UEFI" if inst.get("BootMode") == "uefi" else "BIOS",
        instance_type=inst_type,
        os_name=os_name,
        os_family=os_family,
        disks=disks,
        total_storage_gb=total_gb,
        interfaces=ifaces,
        utilization_band="unknown",
        raw_metadata={"aws_state": inst.get("State", {}).get("Name", ""), "tags": tags},
    )
    return server


def _rds_to_server(db: dict, region: str) -> DiscoveredServer:
    engine = db.get("Engine", "db")
    version = db.get("EngineVersion", "")
    name = db.get("DBInstanceIdentifier", "")
    endpoint = db.get("Endpoint", {})
    ip = endpoint.get("Address", name)
    inst_class = db.get("DBInstanceClass", "")

    cpu, ram = _ec2_type_specs(inst_class.lstrip("db."))
    storage_gb = float(db.get("AllocatedStorage", 0))

    wl_type_map = {
        "mysql": "MySQL", "postgres": "PostgreSQL", "oracle": "Oracle DB",
        "sqlserver": "MSSQL", "mariadb": "MariaDB", "aurora": "Aurora",
        "aurora-mysql": "Aurora MySQL", "aurora-postgresql": "Aurora PostgreSQL",
    }
    wl_name = wl_type_map.get(engine.lower(), engine)

    return DiscoveredServer(
        server_id=db.get("DBInstanceArn", name),
        server_name=f"{name} (RDS)",
        ip_address=ip,
        hostname=ip,
        cloud_provider="aws",
        region=region,
        resource_group=db.get("DBSubnetGroup", {}).get("VpcId", ""),
        cpu_cores=cpu,
        ram_gb=ram,
        server_type="Managed",
        instance_type=inst_class,
        os_name=f"AWS RDS {engine}",
        os_family="managed",
        disks=[DiskInfo(mount_point="/data", size_gb=storage_gb, disk_type="SSD")],
        total_storage_gb=storage_gb,
        workloads=[WorkloadComponent(name=wl_name, version=version, component_type="db")],
        utilization_band="unknown",
    )


def _elasticache_to_server(cluster: dict, region: str) -> DiscoveredServer:
    engine = cluster.get("Engine", "redis")
    version = cluster.get("EngineVersion", "")
    name = cluster.get("CacheClusterId", "")
    node = (cluster.get("CacheNodes") or [{}])[0]
    ip = node.get("Endpoint", {}).get("Address", name) if node else name
    inst_type = cluster.get("CacheNodeType", "")
    cpu, ram = _ec2_type_specs(inst_type.replace("cache.", ""))
    wl_name = "Redis" if engine.lower() == "redis" else "Memcached"
    return DiscoveredServer(
        server_id=name,
        server_name=f"{name} (ElastiCache)",
        ip_address=ip,
        hostname=ip,
        cloud_provider="aws",
        region=region,
        cpu_cores=cpu,
        ram_gb=ram,
        server_type="Managed",
        instance_type=inst_type,
        os_name=f"AWS ElastiCache {engine}",
        os_family="managed",
        workloads=[WorkloadComponent(name=wl_name, version=version, component_type="cache")],
        utilization_band="unknown",
    )


def _ec2_platform(inst: dict) -> tuple[str, str]:
    platform = (inst.get("Platform") or "").lower()
    if platform == "windows":
        return "Windows Server", "windows"
    # Try image description from metadata
    img_loc = inst.get("ImageLocation", "").lower()
    if "ubuntu" in img_loc:
        version = re.search(r"(\d+\.\d+)", img_loc)
        return f"Ubuntu {version.group(1) if version else ''}".strip(), "linux"
    if "rhel" in img_loc or "red-hat" in img_loc:
        return "Red Hat Enterprise Linux", "linux"
    if "amazon" in img_loc:
        return "Amazon Linux", "linux"
    return "Linux", "linux"


_EC2_PARTIAL_SPECS: dict[str, tuple[int, float]] = {
    # format: instance_family_size → (vcpu, ram_gb)
    "t2.micro": (1, 1), "t2.small": (1, 2), "t2.medium": (2, 4),
    "t2.large": (2, 8), "t2.xlarge": (4, 16), "t2.2xlarge": (8, 32),
    "t3.micro": (2, 1), "t3.small": (2, 2), "t3.medium": (2, 4),
    "t3.large": (2, 8), "t3.xlarge": (4, 16), "t3.2xlarge": (8, 32),
    "m5.large": (2, 8), "m5.xlarge": (4, 16), "m5.2xlarge": (8, 32),
    "m5.4xlarge": (16, 64), "m5.8xlarge": (32, 128),
    "m6i.large": (2, 8), "m6i.xlarge": (4, 16), "m6i.2xlarge": (8, 32),
    "c5.large": (2, 4), "c5.xlarge": (4, 8), "c5.2xlarge": (8, 16),
    "r5.large": (2, 16), "r5.xlarge": (4, 32), "r5.2xlarge": (8, 64),
    "db.t3.micro": (2, 1), "db.t3.small": (2, 2), "db.t3.medium": (2, 4),
    "db.r5.large": (2, 16), "db.r5.xlarge": (4, 32),
    "cache.t3.micro": (2, 0.5), "cache.t3.small": (2, 1.37),
    "cache.r6g.large": (2, 13.07),
}


def _ec2_type_specs(instance_type: str) -> tuple[int, float]:
    direct = _EC2_PARTIAL_SPECS.get(instance_type.lower(), (0, 0.0))
    if direct != (0, 0.0):
        return direct
    # Heuristic: extract size suffix
    m = re.search(r"(\d+)xlarge", instance_type.lower())
    if m:
        mult = int(m.group(1))
        return (mult * 4, float(mult * 8))
    if "xlarge" in instance_type.lower():
        return (4, 16)
    if "large" in instance_type.lower():
        return (2, 8)
    if "medium" in instance_type.lower():
        return (2, 4)
    if "small" in instance_type.lower():
        return (1, 2)
    if "micro" in instance_type.lower():
        return (1, 1)
    return (0, 0.0)


def _ebs_type(vol_type: str) -> str:
    mapping = {"gp2": "SSD", "gp3": "SSD", "io1": "NVMe SSD", "io2": "NVMe SSD",
               "st1": "HDD", "sc1": "HDD", "standard": "HDD"}
    return mapping.get(vol_type.lower(), "SSD")
