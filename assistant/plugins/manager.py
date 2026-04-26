from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BasePlugin(ABC):
    """Base class for all assistant plugins."""
    
    def __init__(self):
        self.name = self.__class__.__name__.lower()
        self.enabled = True

    @abstractmethod
    def initialize(self):
        """Initialize the plugin."""
        pass

    @abstractmethod
    def get_commands(self) -> List[Dict[str, Any]]:
        """Return a list of custom commands or tools this plugin provides."""
        return []

class ToolPlugin(BasePlugin):
    """A plugin that provides new tools for the executor."""
    
    @abstractmethod
    def run(self, args: str) -> Dict[str, Any]:
        """Run the tool logic."""
        pass
