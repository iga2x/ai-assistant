from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
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

    @abstractmethod
    def execute(self, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        pass
