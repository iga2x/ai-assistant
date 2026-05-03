from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    def __init__(self, shell=None):
        self.shell = shell

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of the tool's purpose."""
        pass

    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute the tool with given arguments.
        
        Default implementation uses self.shell if available.
        """
        command = f"{self.name} {args}"
        if self.shell:
            return self.shell.execute(command)
        
        # Fallback if no shell provided
        import subprocess
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300, cwd=cwd)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}

