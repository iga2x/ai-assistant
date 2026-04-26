import subprocess
from typing import Dict, Any
from assistant.tools.base import BaseTool

class NmapTool(BaseTool):
    @property
    def name(self) -> str:
        return "nmap"

    @property
    def description(self) -> str:
        return "Network exploration tool and security / port scanner."

    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        command = f"nmap {args}"
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300, # Nmap can take a while
                cwd=cwd
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
