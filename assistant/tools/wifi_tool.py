import subprocess
import re
from typing import Dict, Any
from assistant.tools.base import BaseTool


class WifiTool(BaseTool):
    """Tool for WiFi scanning operations using nmcli or iwconfig."""

    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute WiFi scan command."""
        command = args.strip().lower()

        if "scan" in command or "list" in command:
            return self.scan_networks()

        return {
            "success": False,
            "stdout": "",
            "stderr": "Unknown WiFi command. Use 'wifi scan' or 'wifi list'.",
            "returncode": -1
        }

    def scan_networks(self) -> Dict[str, Any]:
        """Scan for available WiFi networks."""
        if self.shell:
            result = self.shell.execute("nmcli dev wifi list")
        else:
            res = subprocess.run(
                ["nmcli", "dev", "wifi", "list"],
                capture_output=True,
                text=True,
                timeout=30
            )
            result = {
                "success": res.returncode == 0,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "returncode": res.returncode
            }


        if result.get("returncode") == 0:
            return {
                "success": True,
                "stdout": self._parse_nmcli_output(result.get("stdout", "")),
                "stderr": "",
                "returncode": 0
            }


        return {
            "success": False,
            "stdout": "",
            "stderr": "WiFi scan failed. Install NetworkManager (nmcli).",
            "returncode": -1
        }

    def _parse_nmcli_output(self, output: str) -> str:
        lines = output.strip().split('\n')
        result_lines = []
        result_lines.append("Available WiFi Networks:")
        result_lines.append("-" * 60)

        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 3:
                continue

            ssid_idx = 1 if len(parts) < 4 else 2
            ssid = parts[ssid_idx].replace('*', '').strip()

            if ssid and ssid != '--':
                signal = parts[-3] if len(parts) >= 4 else "N/A"
                security = parts[-2] if len(parts) >= 3 else "N/A"
                status = " (CONNECTED)" if '*' in line else ""
                result_lines.append(f"  • {ssid}{status}")
                result_lines.append(f"    Signal: {signal} | Security: {security}")

        return "\n".join(result_lines)

    @property
    def name(self) -> str:
        return "wifi"

    @property
    def description(self) -> str:
        return "Scan and list available WiFi networks"
