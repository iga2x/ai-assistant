import re
import time
from typing import Dict, Any
from assistant.tools.base import BaseTool


class HydraTool(BaseTool):
    """Hydra password brute force tool with progress tracking."""

    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute hydra with progress monitoring."""
        command = f"hydra {args} -V"

        try:
            import subprocess
            process = subprocess.Popen(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            output_lines = []
            passwords_found = []

            for line in process.stdout:
                output_lines.append(line.strip())

                if '[' in line and ']' in line:
                    if 'password' in line.lower():
                        match = re.search(r'password:\s*(\S+)', line)
                        if match:
                            passwords_found.append(match.group(1))
                            result_str = f"\n[bold green]PASSWORD FOUND:[/bold green] {match.group(1)}"
                            print(result_str)

            returncode = process.wait(timeout=600)

            output = '\n'.join(output_lines)

            return {
                "success": True,
                "stdout": output,
                "stderr": "",
                "returncode": returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Hydra timed out (10 min timeout)",
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
        return "hydra"

    @property
    def description(self) -> str:
        return "Hydra password brute force with real-time progress tracking"
