import subprocess
from typing import Dict, Any
from assistant.tools.base import BaseTool


class SubzyTool(BaseTool):
    """Subzy subdomain takeover vulnerability scanner."""

    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute subzy and parse results."""
        command = f"subzy run {args}"

        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Subzy timed out (5 min timeout)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    @property
    def name(self) -> str:
        return "subzy"

    @property
    def description(self) -> str:
        return "Subzy subdomain takeover vulnerability scanner"
