"""
scanner/onprem.py
On-premises network scanner.

Discovery strategy (best-effort, graceful fallback at each level):
  1. nmap  — host discovery + port scan in the CIDR
  2. SSH   — paramiko (Linux/Unix): uname, lscpu, free, df, /etc/os-release,
              systemctl list-units, netstat, dmidecode, lsblk
  3. WinRM — pywinrm (Windows): WMI queries for OS, CPU, RAM, disk, services
  4. SNMP  — pysnmp fallback for network-only devices (switches/routers)
  5. Banner grab — extract OS hints from SSH/HTTP banners when creds absent

All levels are optional — missing binaries/creds reduce fidelity, never crash.
"""
from __future__ import annotations

import ipaddress
import logging
import re
import shutil
import socket
import subprocess
import threading
from typing import Callable

from .models import (
    DiscoveredServer,
    DiskInfo,
    NetworkInterface,
    ScanTarget,
    WorkloadComponent,
)

log = logging.getLogger(__name__)

# ─── Well-known service map (port → workload type + name hint) ─────────────────
_PORT_SERVICES: dict[int, tuple[str, str]] = {
    22:   ("ssh",    "SSH"),
    80:   ("web",    "HTTP"),
    443:  ("web",    "HTTPS"),
    3306: ("db",     "MySQL"),
    5432: ("db",     "PostgreSQL"),
    1433: ("db",     "MSSQL"),
    1521: ("db",     "Oracle DB"),
    5984: ("db",     "CouchDB"),
    27017:("db",     "MongoDB"),
    6379: ("cache",  "Redis"),
    11211:("cache",  "Memcached"),
    9200: ("search", "Elasticsearch"),
    8080: ("app",    "HTTP-Alt"),
    8443: ("app",    "HTTPS-Alt"),
    8009: ("app",    "ApacheTomcat-AJP"),
    8005: ("app",    "ApacheTomcat-Control"),
    9090: ("app",    "AppServer"),
    4848: ("app",    "GlassFish"),
    7001: ("app",    "WebLogic"),
    9001: ("app",    "JBoss"),
    25:   ("mail",   "SMTP"),
    143:  ("mail",   "IMAP"),
    110:  ("mail",   "POP3"),
    389:  ("ldap",   "LDAP"),
    636:  ("ldap",   "LDAPS"),
    2181: ("queue",  "ZooKeeper"),
    9092: ("queue",  "Kafka"),
    5672: ("queue",  "RabbitMQ"),
    61616:("queue",  "ActiveMQ"),
    3389: ("rdp",    "RDP"),
    5900: ("vnc",    "VNC"),
    161:  ("snmp",   "SNMP"),
}

# Common TCP ports to scan
_COMMON_PORTS = ",".join(str(p) for p in sorted(_PORT_SERVICES.keys()))


# ─── nmap helpers ──────────────────────────────────────────────────────────────

def _nmap_available() -> bool:
    return shutil.which("nmap") is not None


def _nmap_scan(cidr: str, timeout: int = 120) -> list[dict]:
    """
    Returns list of dicts: {ip, hostname, state, open_ports: [int]}
    Uses nmap host discovery + port scan.  Falls back to socket ping sweep.
    """
    if not _nmap_available():
        log.warning("nmap not found — using socket sweep fallback")
        return _socket_sweep(cidr)

    cmd = [
        "nmap", "-sV", "--open", "-T4",
        f"-p{_COMMON_PORTS}",
        "--host-timeout", f"{timeout}s",
        "-oX", "-",            # XML output on stdout
        cidr,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 30
        )
        return _parse_nmap_xml(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        log.warning("nmap scan failed: %s", exc)
        return _socket_sweep(cidr)


def _parse_nmap_xml(xml: str) -> list[dict]:
    """Parse nmap XML output — lightweight without lxml dependency."""
    hosts = []
    # Match each <host> block
    for host_block in re.findall(r"<host\b[^>]*>(.*?)</host>", xml, re.DOTALL):
        # Status
        status_m = re.search(r'<status state="(\w+)"', host_block)
        if not status_m or status_m.group(1) != "up":
            continue
        # IP
        addr_m = re.search(r'<address addr="([\d.]+)" addrtype="ipv4"', host_block)
        if not addr_m:
            continue
        ip = addr_m.group(1)
        # Hostname
        hn_m = re.search(r'<hostname name="([^"]+)"', host_block)
        hostname = hn_m.group(1) if hn_m else ""
        # Open ports + service banners
        open_ports: list[int] = []
        service_hints: dict[int, str] = {}
        for port_m in re.finditer(
            r'<port protocol="tcp" portid="(\d+)">(.*?)</port>', host_block, re.DOTALL
        ):
            port_num = int(port_m.group(1))
            port_block = port_m.group(2)
            state_m = re.search(r'<state state="(\w+)"', port_block)
            if state_m and state_m.group(1) == "open":
                open_ports.append(port_num)
                svc_m = re.search(
                    r'<service[^>]+(?:name="([^"]*)")?[^>]*(?:product="([^"]*)")?[^>]*(?:version="([^"]*)")?',
                    port_block,
                )
                if svc_m:
                    svc_parts = [p for p in svc_m.groups() if p]
                    service_hints[port_num] = " ".join(svc_parts)

        hosts.append({
            "ip": ip,
            "hostname": hostname,
            "state": "up",
            "open_ports": open_ports,
            "service_hints": service_hints,
        })
    return hosts


def _socket_sweep(cidr: str) -> list[dict]:
    """Fallback: parallel TCP connect on common ports."""
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return []

    results: list[dict] = []
    lock = threading.Lock()

    def _probe(ip_str: str) -> None:
        open_ports: list[int] = []
        for port in [22, 80, 443, 3306, 5432, 1433, 3389, 8080, 8443, 5900]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.0)
                if s.connect_ex((ip_str, port)) == 0:
                    open_ports.append(port)
                s.close()
            except OSError:
                pass
        if open_ports:
            try:
                hn = socket.gethostbyaddr(ip_str)[0]
            except socket.herror:
                hn = ""
            with lock:
                results.append({
                    "ip": ip_str,
                    "hostname": hn,
                    "state": "up",
                    "open_ports": open_ports,
                    "service_hints": {},
                })

    threads = [threading.Thread(target=_probe, args=(str(ip),), daemon=True)
               for ip in network.hosts()]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    return results


# ─── SSH discovery ─────────────────────────────────────────────────────────────

def _ssh_available() -> bool:
    try:
        import paramiko  # noqa: F401
        return True
    except ImportError:
        return False


def _ssh_run(client, cmd: str) -> str:
    try:
        _, stdout, _ = client.exec_command(cmd, timeout=15)
        return stdout.read().decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def _parse_key_value(text: str, sep: str = "=") -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if sep in line:
            k, _, v = line.partition(sep)
            result[k.strip()] = v.strip().strip('"')
    return result


def _ssh_enrich(server: DiscoveredServer, target: ScanTarget) -> None:
    """Connect over SSH and enrich the DiscoveredServer in-place."""
    if not _ssh_available():
        log.debug("paramiko not installed — skipping SSH enrichment")
        return

    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs: dict = {"hostname": server.ip_address, "timeout": 10}

    if target.ssh_key_path:
        try:
            connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key_file(
                target.ssh_key_path
            )
        except Exception:
            pass
    if target.ssh_username:
        connect_kwargs["username"] = target.ssh_username
    if target.ssh_password:
        connect_kwargs["password"] = target.ssh_password

    try:
        client.connect(**connect_kwargs)
    except Exception as exc:
        log.debug("SSH connect to %s failed: %s", server.ip_address, exc)
        return

    try:
        # ── OS release ──
        os_rel = _parse_key_value(_ssh_run(client, "cat /etc/os-release 2>/dev/null || cat /etc/lsb-release 2>/dev/null"), "=")
        if not os_rel:
            uname_raw = _ssh_run(client, "uname -srm")
            server.os_name = uname_raw
            server.os_family = "linux"
        else:
            server.os_name = os_rel.get("PRETTY_NAME") or os_rel.get("DISTRIB_DESCRIPTION", "Linux")
            server.os_family = "linux"
            server.os_version = os_rel.get("VERSION_ID", "")

        # ── CPU ──
        cpu_info = _ssh_run(client, "nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null")
        if cpu_info.isdigit():
            server.cpu_cores = int(cpu_info)
        arch_out = _ssh_run(client, "uname -m")
        server.architecture = "64 bit" if "64" in arch_out else "32 bit"
        instance_type_out = _ssh_run(
            client,
            "curl -sf --max-time 2 http://169.254.169.254/latest/meta-data/instance-type 2>/dev/null "
            "|| curl -sf --max-time 2 -H 'Metadata:true' http://169.254.169.254/metadata/instance?api-version=2021-02-01 2>/dev/null "
            "| python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get('compute',{}).get('vmSize',''))\" 2>/dev/null"
        )
        if instance_type_out and len(instance_type_out) < 60:
            server.instance_type = instance_type_out

        # ── RAM ──
        meminfo = _ssh_run(client, "grep MemTotal /proc/meminfo")
        m = re.search(r"(\d+)", meminfo)
        if m:
            server.ram_gb = round(int(m.group(1)) / 1024 / 1024, 1)

        # ── Disk ──
        df_out = _ssh_run(client, "df -BG --output=target,size,used,pcent,fstype 2>/dev/null | tail -n +2")
        lsblk_out = _ssh_run(client, "lsblk -d -o NAME,SIZE,TYPE,ROTA 2>/dev/null")
        server.disks = _parse_disks_linux(df_out, lsblk_out)
        server.total_storage_gb = sum(d.size_gb for d in server.disks)

        # ── Utilization ──
        cpu_idle = _ssh_run(client, "vmstat 1 2 2>/dev/null | tail -1 | awk '{print $15}'")
        try:
            server.cpu_util_pct = round(100.0 - float(cpu_idle), 1)
        except ValueError:
            pass
        mem_avail = _ssh_run(client, "grep MemAvailable /proc/meminfo")
        m2 = re.search(r"(\d+)", mem_avail)
        if m2 and server.ram_gb > 0:
            avail_gb = int(m2.group(1)) / 1024 / 1024
            server.ram_util_pct = round(100.0 * (1 - avail_gb / server.ram_gb), 1)

        # ── Network interfaces ──
        ip_out = _ssh_run(client, "ip -o addr show 2>/dev/null || ifconfig -a 2>/dev/null")
        server.interfaces = _parse_interfaces_linux(ip_out)

        # ── Workloads ──
        server.workloads = _discover_workloads_ssh(client)

        # ── Server type / boot ──
        dmi = _ssh_run(client, "sudo dmidecode -t system 2>/dev/null || cat /sys/class/dmi/id/sys_vendor 2>/dev/null")
        if any(v in dmi.lower() for v in ["vmware", "virtualbox", "kvm", "xen", "microsoft"]):
            server.server_type = "Virtual"
        elif "physical" in dmi.lower():
            server.server_type = "Physical"

        boot_mode = _ssh_run(client, "[ -d /sys/firmware/efi ] && echo UEFI || echo BIOS")
        server.boot_type = "UEFI" if "UEFI" in boot_mode else "BIOS"

    finally:
        client.close()


def _parse_disks_linux(df_out: str, lsblk_out: str) -> list[DiskInfo]:
    disks: list[DiskInfo] = []
    # Rotation map from lsblk: 0=SSD, 1=HDD
    rotation: dict[str, bool] = {}
    for line in lsblk_out.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            rotation[parts[0]] = parts[3] == "1"
    for line in df_out.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            size_gb = float(parts[1].rstrip("G"))
            used_gb = float(parts[2].rstrip("G"))
        except ValueError:
            continue
        rota = next((v for k, v in rotation.items() if k in parts[0]), None)
        disk_type = "HDD" if rota else "SSD" if rota is False else "unknown"
        disks.append(DiskInfo(
            mount_point=parts[0],
            size_gb=size_gb,
            used_gb=used_gb,
            disk_type=disk_type,
        ))
    return disks


def _parse_interfaces_linux(ip_out: str) -> list[NetworkInterface]:
    ifaces: list[NetworkInterface] = []
    seen: set[str] = set()
    for m in re.finditer(r"(\w+)\s+inet\s+([\d.]+)/(\d+)", ip_out):
        iface_name, ip, prefix = m.group(1), m.group(2), m.group(3)
        if ip.startswith("127.") or iface_name == "lo":
            continue
        if ip in seen:
            continue
        seen.add(ip)
        ip_type = "public" if not _is_private(ip) else "private"
        ifaces.append(NetworkInterface(
            interface_name=iface_name,
            ip_address=ip,
            ip_type=ip_type,
            subnet=f"{ip}/{prefix}",
        ))
    return ifaces


def _is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return True


def _discover_workloads_ssh(client) -> list[WorkloadComponent]:
    """Detect running workloads via process list + service detection."""
    workloads: list[WorkloadComponent] = []
    ps_out = _ssh_run(client, "ps aux 2>/dev/null || ps -ef 2>/dev/null")
    ss_out = _ssh_run(client, "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")

    _check_pattern(workloads, ps_out, "mysqld", "MySQL", "db", _get_version_from_ssh(client, "mysql --version 2>/dev/null"))
    _check_pattern(workloads, ps_out, "postgres", "PostgreSQL", "db", _get_version_from_ssh(client, "psql --version 2>/dev/null"))
    _check_pattern(workloads, ps_out, "mongod", "MongoDB", "db", _get_version_from_ssh(client, "mongod --version 2>/dev/null | head -1"))
    _check_pattern(workloads, ps_out, "oracle", "Oracle DB", "db", "")
    _check_pattern(workloads, ps_out, "nginx", "nginx", "web", _get_version_from_ssh(client, "nginx -v 2>&1 | head -1"))
    _check_pattern(workloads, ps_out, "apache2|httpd", "Apache HTTPD", "web", _get_version_from_ssh(client, "apache2 -v 2>/dev/null || httpd -v 2>/dev/null | head -1"))
    _check_pattern(workloads, ps_out, "catalina|tomcat", "ApacheTomcat", "app", "")
    _check_pattern(workloads, ps_out, "node ", "Node.js", "app", _get_version_from_ssh(client, "node --version 2>/dev/null"))
    _check_pattern(workloads, ps_out, "java ", "Java App", "app", _get_version_from_ssh(client, "java -version 2>&1 | head -1"))
    _check_pattern(workloads, ps_out, "redis-server", "Redis", "cache", _get_version_from_ssh(client, "redis-server --version 2>/dev/null"))
    _check_pattern(workloads, ps_out, "memcached", "Memcached", "cache", "")
    _check_pattern(workloads, ps_out, "rabbitmq", "RabbitMQ", "queue", "")
    _check_pattern(workloads, ps_out, "kafka", "Kafka", "queue", "")
    return workloads


def _get_version_from_ssh(client, cmd: str) -> str:
    raw = _ssh_run(client, cmd)
    m = re.search(r"[\d]+\.[\d.]+", raw)
    return m.group(0) if m else ""


def _check_pattern(workloads: list, text: str, pattern: str, name: str, wtype: str, version: str) -> None:
    if re.search(pattern, text, re.IGNORECASE):
        workloads.append(WorkloadComponent(name=name, version=version, component_type=wtype))


# ─── WinRM discovery ───────────────────────────────────────────────────────────

def _winrm_available() -> bool:
    try:
        import winrm  # noqa: F401
        return True
    except ImportError:
        return False


def _winrm_enrich(server: DiscoveredServer, target: ScanTarget) -> None:
    if not _winrm_available():
        log.debug("pywinrm not installed — skipping WinRM enrichment")
        return
    try:
        import winrm
        s = winrm.Session(
            target=server.ip_address,
            auth=(target.winrm_username, target.winrm_password),
            transport="ntlm",
        )
        # Get OS info
        os_result = s.run_ps(
            "Get-WmiObject -Class Win32_OperatingSystem | "
            "Select-Object -Property Caption,Version,OSArchitecture,TotalVisibleMemorySize | "
            "ConvertTo-Json"
        )
        if os_result.status_code == 0:
            import json
            data = json.loads(os_result.std_out.decode())
            server.os_name = data.get("Caption", "Windows")
            server.os_family = "windows"
            server.os_version = data.get("Version", "")
            server.architecture = "64 bit" if "64" in str(data.get("OSArchitecture", "")) else "32 bit"
            mem_kb = data.get("TotalVisibleMemorySize", 0)
            server.ram_gb = round(mem_kb / 1024 / 1024, 1) if mem_kb else 0.0

        # CPU
        cpu_r = s.run_ps(
            "Get-WmiObject Win32_ComputerSystem | Select-Object -ExpandProperty NumberOfLogicalProcessors"
        )
        if cpu_r.status_code == 0:
            try:
                server.cpu_cores = int(cpu_r.std_out.decode().strip())
            except ValueError:
                pass

        # Disk
        disk_r = s.run_ps(
            "Get-WmiObject Win32_LogicalDisk | Where-Object {$_.DriveType -eq 3} | "
            "Select-Object DeviceID,Size,FreeSpace | ConvertTo-Json"
        )
        if disk_r.status_code == 0:
            import json
            disks_raw = json.loads(disk_r.std_out.decode())
            if isinstance(disks_raw, dict):
                disks_raw = [disks_raw]
            for dr in disks_raw:
                size_gb = round(int(dr.get("Size", 0)) / 1e9, 1)
                used_gb = round((int(dr.get("Size", 0)) - int(dr.get("FreeSpace", 0))) / 1e9, 1)
                server.disks.append(DiskInfo(
                    mount_point=str(dr.get("DeviceID", "")),
                    size_gb=size_gb,
                    used_gb=used_gb,
                    disk_type="HDD",
                ))
            server.total_storage_gb = sum(d.size_gb for d in server.disks)

        # Services → workloads
        svc_r = s.run_ps(
            "Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object -ExpandProperty Name | ConvertTo-Json"
        )
        if svc_r.status_code == 0:
            import json
            svc_names = json.loads(svc_r.std_out.decode())
            wl_map = {
                "MSSQLSERVER": ("MSSQL", "db"), "mysql": ("MySQL", "db"),
                "PostgreSQL": ("PostgreSQL", "db"), "W3SVC": ("IIS", "web"),
                "Tomcat": ("ApacheTomcat", "app"),
                "redis": ("Redis", "cache"),
            }
            for svc_name in svc_names:
                for key, (name, wtype) in wl_map.items():
                    if key.lower() in svc_name.lower():
                        server.workloads.append(WorkloadComponent(name=name, component_type=wtype))

        server.server_type = "Virtual"
        server.boot_type = "BIOS"
        server.os_family = "windows"
    except Exception as exc:
        log.debug("WinRM enrichment failed for %s: %s", server.ip_address, exc)


# ─── Main entry point ──────────────────────────────────────────────────────────

def scan_onprem(
    target: ScanTarget,
    progress_cb: Callable[[int, str], None] | None = None,
) -> list[DiscoveredServer]:
    """
    Full on-premises scan.  Returns list of DiscoveredServer.
    progress_cb(pct, message) is called with updates.
    """
    def _cb(pct: int, msg: str) -> None:
        log.info("[onprem %d%%] %s", pct, msg)
        if progress_cb:
            progress_cb(pct, msg)

    cidr = target.network_range or "192.168.1.0/24"
    _cb(5, f"Starting host discovery on {cidr}")

    raw_hosts = _nmap_scan(cidr, timeout=target.timeout_seconds)
    _cb(20, f"Found {len(raw_hosts)} live hosts")

    servers: list[DiscoveredServer] = []
    total = max(len(raw_hosts), 1)

    for idx, host in enumerate(raw_hosts):
        ip = host["ip"]
        _cb(20 + int(70 * idx / total), f"Scanning {ip}")

        server = DiscoveredServer(
            server_id=ip.replace(".", "-"),
            server_name=host.get("hostname") or ip,
            ip_address=ip,
            hostname=host.get("hostname", ""),
            cloud_provider="onprem",
            region="OnPrem",
        )

        # Add workload hints from port scan
        for port in host.get("open_ports", []):
            if port in _PORT_SERVICES:
                wl_type, wl_name = _PORT_SERVICES[port]
                if wl_type not in ("ssh", "rdp", "snmp", "vnc"):
                    server.workloads.append(WorkloadComponent(
                        name=wl_name,
                        component_type=wl_type,
                        port=port,
                    ))
        # Add primary IP interface
        server.interfaces.append(NetworkInterface(
            interface_name="eth0",
            ip_address=ip,
            ip_type="public" if not _is_private(ip) else "private",
        ))

        # Deep scan
        if target.deep_scan:
            has_ssh = 22 in host.get("open_ports", [])
            has_rdp = 3389 in host.get("open_ports", [])

            if has_ssh and target.ssh_username:
                _ssh_enrich(server, target)
            elif has_rdp and target.winrm_username:
                _winrm_enrich(server, target)
            else:
                _guess_os_from_ports(server, host)

        _classify_utilization(server)
        servers.append(server)

    _cb(95, "Finalizing results")
    return servers


def _guess_os_from_ports(server: DiscoveredServer, host: dict) -> None:
    """Heuristic OS detection when no credentials are available."""
    ports = set(host.get("open_ports", []))
    hints = " ".join(host.get("service_hints", {}).values()).lower()
    if 3389 in ports or "windows" in hints:
        server.os_name = "Windows Server"
        server.os_family = "windows"
    elif 22 in ports:
        server.os_name = "Linux"
        server.os_family = "linux"


def _classify_utilization(server: DiscoveredServer) -> None:
    """Set utilization_band based on CPU + RAM utilization metrics."""
    if server.cpu_util_pct < 0 and server.ram_util_pct < 0:
        server.utilization_band = "unknown"
        return
    avg = 0.0
    count = 0
    if server.cpu_util_pct >= 0:
        avg += server.cpu_util_pct
        count += 1
    if server.ram_util_pct >= 0:
        avg += server.ram_util_pct
        count += 1
    avg = avg / count if count else 0
    if avg < 30:
        server.utilization_band = "underutilized"
    elif avg < 65:
        server.utilization_band = "moderate"
    else:
        server.utilization_band = "utilized"
