import subprocess
import os
from typing import Dict, Any
from assistant.tools.base import BaseTool


class VolatilityTool(BaseTool):
    """Volatility memory forensics tool with result parsing."""

    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute volatility and parse forensics results."""
        # Use 'vol' (Volatility 3) or fallback to 'vol.py' (Volatility 2)
        import shutil
        binary = "vol" if shutil.which("vol") else "vol.py"
        command = f"{binary} {args}"

        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                parsed_output = self._parse_volatility_results(result.stdout)
                return {
                    "success": True,
                    "stdout": parsed_output,
                    "stderr": "",
                    "returncode": 0
                }
            else:
                return {
                    "success": False,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Volatility timed out (5 min timeout)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def _parse_volatility_results(self, output: str) -> str:
        """Parse volatility JSON output."""
        try:
            import json
            if 'vol_results.json' in output:
                if os.path.exists('vol_results.json'):
                    with open('vol_results.json', 'r') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and 'processes' in data:
                            processes = data['processes']
                            if processes:
                                result_str = f"\n[bold cyan]MEMORY FORENSICS RESULTS:[/bold cyan]\n"
                                result_str += f"Processes found: {len(processes)}\n"
                                for proc in processes[:10]:
                                    result_str += f"  - {proc.get('name', 'unknown')}\n"
                                return result_str
        except Exception:
            return output

        return output

    @property
    def name(self) -> str:
        return "volatility"

    @property
    def description(self) -> str:
        return "Volatility memory forensics with JSON parsing"
