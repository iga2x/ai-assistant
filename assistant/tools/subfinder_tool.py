import subprocess
from typing import Dict, Any
from assistant.tools.base import BaseTool


class SubfinderTool(BaseTool):
    """Subfinder subdomain enumeration with result parsing."""

    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute subfinder and parse results."""
        command = f"subfinder {args} -silent"

        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=180
            )

            if result.returncode == 0:
                parsed_output = self._parse_subfinder_results(result.stdout)
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
                "stderr": "Subfinder timed out (3 min timeout)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def _parse_subfinder_results(self, output: str) -> str:
        """Parse subfinder output to count subdomains."""
        subdomains = [line.strip() for line in output.split('\n') if line.strip()]

        if subdomains:
            header = f"\n[bold cyan]SUBDOMAINS FOUND:[/bold cyan] {len(subdomains)} total\n"
            return header + '\n'.join(subdomains[:50])

        return output

    @property
    def name(self) -> str:
        return "subfinder"

    @property
    def description(self) -> str:
        return "Subfinder subdomain enumeration with result parsing"
