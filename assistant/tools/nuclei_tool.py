import json
import re
from typing import Dict, Any
from assistant.tools.base import BaseTool


class NucleiTool(BaseTool):
    """Nuclei vulnerability scanner wrapper with JSON parsing."""

    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute nuclei and parse JSON output."""
        command = f"nuclei {args}"

        try:
            import subprocess
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                parsed_output = self._parse_nuclei_json(result.stdout)
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
                "stderr": "Nuclei scan timed out (5 min timeout)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def _parse_nuclei_json(self, output: str) -> str:
        """Parse nuclei JSON output into readable format."""
        try:
            results = []
            lines = output.split('\n')
            for line in lines:
                try:
                    data = json.loads(line)
                    if 'templateID' in data:
                        severity = data.get('info', {}).get('severity', 'INFO')
                        template = data.get('templateID', 'unknown')
                        host = data.get('matched-at', 'unknown')
                        vuln_name = data.get('info', {}).get('name', 'unknown')

                        result_line = f"[{severity}] {vuln_name} on {host} (Template: {template})"
                        results.append(result_line)
                except:
                    continue

            if results:
                return '\n'.join(results)
            return output

        except Exception:
            return output

    @property
    def name(self) -> str:
        return "nuclei"

    @property
    def description(self) -> str:
        return "Nuclei vulnerability scanner with JSON parsing"
