import re
from typing import Dict, Any
from assistant.tools.base import BaseTool


class FfufTool(BaseTool):
    """FFUF web fuzzer wrapper with result parsing."""

    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute ffuf and parse fuzzing results."""
        command = f"ffuf {args}"

        try:
            import subprocess
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                parsed_output = self._parse_ffuf_results(result.stdout)
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
                "stderr": "FFUF scan timed out (5 min timeout)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def _parse_ffuf_results(self, output: str) -> str:
        """Parse ffuf output to extract findings."""
        results = []
        lines = output.split('\n')

        for line in lines:
            line = line.strip()

            if 'Status:' in line and '200' in line:
                parts = line.split()
                if len(parts) >= 2:
                    url = parts[0]
                    results.append(f"\n[bold green]SUCCESS:[/bold green] {line}")
                    continue

            if 'Status:' in line and '403' in line:
                parts = line.split()
                if len(parts) >= 2:
                    url = parts[0]
                    results.append(f"\n[yellow]FORBIDDEN:[/yellow] {line}")

        return '\n'.join(results) if results else output

    @property
    def name(self) -> str:
        return "ffuf"

    @property
    def description(self) -> str:
        return "FFUF web fuzzer with result parsing"
