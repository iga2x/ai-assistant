import re
from typing import Dict, Any
from assistant.tools.base import BaseTool


class SqlmapTool(BaseTool):
    """SQLMap SQL injection tester wrapper with result parsing."""

    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute sqlmap and parse results."""
        command = f"sqlmap {args} --batch --random-agent"

        try:
            import subprocess
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode == 0:
                parsed_output = self._parse_sqlmap_results(result.stdout)
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
                "stderr": "SQLMap scan timed out (10 min timeout)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def _parse_sqlmap_results(self, output: str) -> str:
        """Parse sqlmap output to extract vulnerabilities."""
        results = []
        lines = output.split('\n')

        in_vuln_section = False
        current_url = None
        vuln_count = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if 'sqlmap identified the following' in line:
                in_vuln_section = True
                results.append(f"\n[bold cyan]VULNERABILITIES FOUND:[/bold cyan]")
                continue

            if in_vuln_section and '---' in line:
                break

            if in_vuln_section:
                if 'sqlmap resumed' not in line and 'requests:' not in line:
                    if 'http' in line:
                        current_url = line.split()[0]
                    if 'injectable' in line.lower() or 'parameter' in line.lower():
                        vuln_count += 1
                        results.append(f"  [{vuln_count}] {line}")

        if vuln_count == 0:
            return output

        return '\n'.join(results) if results else output

    @property
    def name(self) -> str:
        return "sqlmap"

    @property
    def description(self) -> str:
        return "SQLMap SQL injection tester with vulnerability parsing"
