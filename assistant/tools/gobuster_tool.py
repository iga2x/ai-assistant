import re
from typing import Dict, Any
from assistant.tools.base import BaseTool


class GobusterTool(BaseTool):
    """Gobuster directory scanner with result parsing."""

    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute gobuster and parse results."""
        command = f"gobuster {args}"

        try:
            import subprocess
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                parsed_output = self._parse_gobuster_results(result.stdout)
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
                "stderr": "Gobuster scan timed out (5 min timeout)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def _parse_gobuster_results(self, output: str) -> str:
        """Parse gobuster output to extract found directories."""
        results = []
        lines = output.split('\n')

        found_dirs = set()
        in_results_section = False

        for line in lines:
            line = line.strip()

            if 'Found:' in line:
                in_results_section = True
                match = re.search(r'Found:\s*(\S+)', line)
                if match:
                    found_dirs.add(match.group(1))
                    result_str = f"\n[bold green]FOUND:[/bold green] {match.group(1)}"
                    results.append(result_str)

            if in_results_section and line == '':
                in_results_section = False

        if found_dirs:
            results.insert(0, f"\n[bold cyan]DIRECTORIES FOUND:[/bold cyan] {len(found_dirs)} total")

        return '\n'.join(results) if results else output

    @property
    def name(self) -> str:
        return "gobuster"

    @property
    def description(self) -> str:
        return "Gobuster directory scanner with result parsing"
