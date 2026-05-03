import platform
import os
import psutil
import socket
from typing import Dict, Any, List
from pydantic import BaseModel

from assistant.system.os_detect import get_os_detailed, get_python_version
from assistant.system.permissions import is_admin

class SystemInfo(BaseModel):
    os_name: str
    os_detailed: str
    architecture: str
    hostname: str
    username: str
    is_admin: bool
    python_version: str
    cpu_count: int
    total_ram_gb: float
    disk_free_gb: float
    shell: str
    shell_path: str
    terminal: str
    local_ip: str
    interfaces: List[str] = []
    network_neighbors: List[str] = []

def get_shell_info() -> Dict[str, str]:
    """Detect the current shell and terminal."""
    shell_path = os.getenv("SHELL", "unknown")
    shell_name = shell_path.split("/")[-1]
    terminal = os.getenv("TERM", "unknown")
    return {
        "shell": shell_name,
        "shell_path": shell_path,
        "terminal": terminal
    }

def get_local_ip(check_ip: str = "1.1.1.1") -> str:
    """Get the local IP address."""
    try:
        # This doesn't actually connect, just gets the interface IP
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((check_ip, 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_network_info(check_ip: str = "1.1.1.1") -> Dict[str, Any]:
    """Get network interfaces and primary IP."""
    interfaces = []
    try:
        import psutil
        for name, addrs in psutil.net_if_addrs().items():
            interfaces.append(name)
    except Exception:
        pass
    
    return {
        "interfaces": interfaces,
        "primary_ip": get_local_ip(check_ip)
    }

def get_network_neighbors() -> List[str]:
    """Get active neighbors from ARP cache/ip neighbor."""
    neighbors = []
    try:
        # Try 'ip neighbor' first (modern linux)
        import subprocess
        result = subprocess.run(["ip", "neighbor", "show"], capture_output=True, text=True, timeout=1.0)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "REACHABLE" in line or "STALE" in line:
                    neighbors.append(line.strip())
        
        # Fallback to /proc/net/arp if needed
        if not neighbors and os.path.exists("/proc/net/arp"):
            with open("/proc/net/arp", "r") as f:
                lines = f.readlines()[1:] # Skip header
                for line in lines:
                    parts = line.split()
                    if len(parts) > 0:
                        neighbors.append(f"IP: {parts[0]}, HW: {parts[3]}")
    except Exception:
        pass
    return neighbors[:10] # Limit to top 10 to avoid bloat

def discover_system(config: Any = None) -> SystemInfo:
    """Gather complete system information."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    shell_info = get_shell_info()
    
    check_ip = config.network.reachability_check_ip if config and hasattr(config, "network") else "1.1.1.1"
    net_info = get_network_info(check_ip)
    
    return SystemInfo(
        os_name=platform.system(),
        os_detailed=get_os_detailed(),
        architecture=platform.machine(),
        hostname=socket.gethostname(),
        username=os.getlogin() if hasattr(os, "getlogin") else os.getenv("USER", "unknown"),
        is_admin=is_admin(),
        python_version=get_python_version(),
        cpu_count=psutil.cpu_count() or 0,
        total_ram_gb=round(mem.total / (1024**3), 2),
        disk_free_gb=round(disk.free / (1024**3), 2),
        shell=shell_info["shell"],
        shell_path=shell_info["shell_path"],
        terminal=shell_info["terminal"],
        local_ip=net_info["primary_ip"],
        interfaces=net_info["interfaces"],
        network_neighbors=get_network_neighbors()
    )
