import shutil
from typing import List, Dict
from pydantic import BaseModel

import subprocess

class ToolInfo(BaseModel):
    name: str
    path: str
    installed: bool
    version: str = "unknown"
    category: str
    risk_level: str

COMMON_TOOLS = {
    "nmap": {"category": "scanner", "risk": "medium", "ver_cmd": "nmap --version"},
    "git": {"category": "development", "risk": "low", "ver_cmd": "git --version"},
    "docker": {"category": "container", "risk": "medium", "ver_cmd": "docker --version"},
    "python3": {"category": "runtime", "risk": "low", "ver_cmd": "python3 --version"},
    "pip": {"category": "package_manager", "risk": "low", "ver_cmd": "pip --version"},
    "curl": {"category": "network", "risk": "low", "ver_cmd": "curl --version"},
    "wget": {"category": "network", "risk": "low", "ver_cmd": "wget --version"},
    "dig": {"category": "recon", "risk": "low", "ver_cmd": "dig -v"},
    "whois": {"category": "recon", "risk": "low", "ver_cmd": "whois --version"},
    "grep": {"category": "utility", "risk": "low", "ver_cmd": "grep --version"},
    "nuclei": {"category": "scanner", "risk": "high", "ver_cmd": "nuclei -version"},
    "subfinder": {"category": "recon", "risk": "medium", "ver_cmd": "subfinder -version"},
}

def get_tool_version(command: str) -> str:
    """Run a version command and parse output."""
    try:
        result = subprocess.run(
            command.split(), 
            capture_output=True, 
            text=True, 
            timeout=2.0
        )
        output = result.stdout or result.stderr
        # Very basic parsing, just get the first line or first few words
        if output:
            return output.split('\n')[0].strip()
    except Exception:
        pass
    return "unknown"

def detect_tools() -> List[ToolInfo]:
    """Detect tools in PATH with version and classification."""
    detected = []
    for tool, meta in COMMON_TOOLS.items():
        path = shutil.which(tool)
        version = "unknown"
        if path:
            version = get_tool_version(meta["ver_cmd"])
            
        detected.append(ToolInfo(
            name=tool,
            path=path or "",
            installed=bool(path),
            version=version,
            category=meta["category"],
            risk_level=meta["risk"]
        ))
    return detected
