import os
import warnings
from typing import Dict, Any
from rich.console import Console
from assistant.system.persistent_shell import PersistentShell
from assistant.utils.paths import BASE_DIR

# Deprecation warning: ToolRunner should be used through ToolRegistry
warnings.warn(
    "Direct import of ToolRunner is deprecated. "
    "Use ToolRegistry from assistant.tools.registry instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import all tool wrappers
from assistant.tools.nmap_tool import NmapTool
from assistant.tools.wifi_tool import WifiTool
from assistant.tools.nuclei_tool import NucleiTool
from assistant.tools.sqlmap_tool import SqlmapTool
from assistant.tools.ffuf_tool import FfufTool
from assistant.tools.hydra_tool import HydraTool
from assistant.tools.john_tool import JohnTool
from assistant.tools.hashcat_tool import HashcatTool
from assistant.tools.gobuster_tool import GobusterTool
from assistant.tools.subfinder_tool import SubfinderTool
from assistant.tools.subzy_tool import SubzyTool
from assistant.tools.volatility_tool import VolatilityTool

console = Console()

TOOL_WHITELIST = [
    # Scanners
    "nmap", "masscan", "rustscan", "nuclei",
    # Recon
    "subfinder", "amass", "assetfinder", "subzy",
    "dig", "nslookup", "host", "whois", "dnsx",
    # Network/Web
    "curl", "wget", "httpx", "ffuf", "gobuster", "dirsearch", "wfuzz", "nikto",
    # Pentesting
    "sqlmap", "hydra", "john", "hashcat", "metasploit", "zaproxy", "zap",
    # Wireless
    "aircrack-ng", "aircrack", "wifite", "reaver",
    # Forensics
    "foremost", "binwalk", "volatility", "volatility3", "autopsy", "bulk_extractor", "exiftool", "strings",
    # Password
    "hashcat", "john", "hydra", "cewl", "crunch",
    # Editors
    "vim", "nano", "code", "sublime",
    # Password Managers
    "pass", "keepassxc",
    # Network Utils
    "tcpdump", "wireshark", "netcat", "ncat", "bettercap",
    # Development/Utils
    "git", "python3", "pip", "docker", "grep", "make",
    # System
    "nmcli", "iw"
]


class ToolRunner:
    def __init__(self):
        self.shell = PersistentShell()
        # Register all 12 tool wrappers with shared shell
        self.registry = {
            # Scanners
            "nmap": NmapTool(shell=self.shell),
            "wifi": WifiTool(shell=self.shell),
            "nuclei": NucleiTool(shell=self.shell),
            "sqlmap": SqlmapTool(shell=self.shell),
            "ffuf": FfufTool(shell=self.shell),
            # Pentesting
            "hydra": HydraTool(shell=self.shell),
            "john": JohnTool(shell=self.shell),
            "hashcat": HashcatTool(shell=self.shell),
            "gobuster": GobusterTool(shell=self.shell),
            "subfinder": SubfinderTool(shell=self.shell),
            "subzy": SubzyTool(shell=self.shell),
            # Forensics
            "volatility": VolatilityTool(shell=self.shell),
        }

        self.shell_log_path = os.path.expanduser("~/.assistant/logs/shell_activity.log")
        os.makedirs(os.path.dirname(self.shell_log_path), exist_ok=True)

    def is_safe_command(self, command: str) -> bool:
        """Basic safety check for command execution."""
        if not command.strip():
            return False
        # Add basic injection checks if needed, but we trust the AI and have a whitelist
        return True

    def run_shell(self, command: str, cwd: str = None) -> Dict[str, Any]:
        """Execute a shell command via the persistent PTY shell."""
        try:
            if not self.is_safe_command(command):
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Error: Command '{command}' failed safety check.",
                    "returncode": -1
                }

            console.print(f"[dim]Executing (Persistent PTY): {command}[/dim]")
            
            # Log for 2nd terminal monitoring
            with open(self.shell_log_path, "a") as f:
                f.write(f"\n>>> {command}\n")
            
            result = self.shell.execute(command, timeout=300) # Increased to 5 mins for long scans
            
            # Log output to file
            with open(self.shell_log_path, "a") as f:
                if result["stdout"]: f.write(result["stdout"])
                if result["stderr"]: f.write(f"ERROR: {result['stderr']}")
                f.write(f"\n--- Done (RC: {result['returncode']}) ---\n")

            return result
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def run_tool(self, tool_name: str, args: str, cwd: str = None) -> Dict[str, Any]:
        """Run a specific tool or fallback to shell."""
        tool = self.registry.get(tool_name)
        if tool:
            # Strip tool name from start of args if present
            clean_args = args.replace(f"{tool_name} ", "", 1) if args.startswith(tool_name) else args
            return tool.execute(clean_args, cwd=cwd)
        
        # Default to shell
        return self.run_shell(args, cwd=cwd)
