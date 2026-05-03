import re
from typing import Dict, Any
from assistant.tools.base import BaseTool


class JohnTool(BaseTool):
    """John the Ripper password cracker with progress tracking."""

    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute john with result parsing."""
        command = f"john {args} --show"

        try:
            import subprocess
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode == 0:
                parsed_output = self._parse_john_results(result.stdout)
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
                "stderr": "John timed out (10 min timeout)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def _parse_john_results(self, output: str) -> str:
        """Parse john output to extract cracked passwords."""
        results = []
        lines = output.split('\n')

        for line in lines:
            line = line.strip()

            if '?' in line and ':' in line:
                parts = line.split(':')
                if len(parts) == 2:
                    hash_part = parts[0].strip()
                    rest = parts[1].strip()

                    if '(' in rest:
                        result_str = f"\n[bold green]CRACKED:[/bold green] {hash_part} -> {rest}"
                        results.append(result_str)

        return '\n'.join(results) if results else output

    @property
    def name(self) -> str:
        return "john"

    @property
    def description(self) -> str:
        return "John the Ripper password cracker with result parsing"
