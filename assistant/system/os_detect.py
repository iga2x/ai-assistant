import platform
import sys

def get_os_detailed() -> str:
    """Get detailed OS information."""
    system = platform.system()
    if system == "Linux":
        # Standard way for modern Linux (Python 3.10+)
        if hasattr(platform, "freedesktop_os_release"):
            try:
                release = platform.freedesktop_os_release()
                return f"{release.get('NAME', 'Linux')} {release.get('VERSION_ID', '')}".strip()
            except Exception:
                pass
        
        # Fallback for older Python or specific cases
        try:
            with open("/etc/os-release") as f:
                d = {}
                for line in f:
                    if "=" in line:
                        k, v = line.rstrip().split("=", 1)
                        d[k] = v.strip('"')
                return f"{d.get('NAME', 'Linux')} {d.get('VERSION_ID', '')}".strip()
        except Exception:
            pass
            
        return f"Linux {platform.release()}"
    elif system == "Darwin":
        return f"macOS {platform.mac_ver()[0]}"
    elif system == "Windows":
        return f"Windows {platform.version()}"
    return f"{system} {platform.release()}"

def get_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
