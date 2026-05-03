"""Memory system interface - defines contract for all memory implementations."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class IMemoryStore(ABC):
    """Interface for memory storage systems."""

    @abstractmethod
    def get(self, name: str) -> Optional[str]:
        """Get entity value by name."""
        pass

    @abstractmethod
    def set(self, name: str, value: str, entity_type: str, confidence: float = 1.0):
        """Set entity value."""
        pass

    @abstractmethod
    def update(self, key: str, value: str, confidence: float = 1.0):
        """Update entity value with confidence check."""
        pass

    @abstractmethod
    def delete(self, name: str):
        """Delete entity by name."""
        pass

    @abstractmethod
    def get_all(self) -> Dict[str, str]:
        """Get all entities as dict."""
        pass

    @abstractmethod
    def list_all(self, category: str = None) -> List[Dict]:
        """List all entities with metadata."""
        pass

    @abstractmethod
    def clear(self):
        """Clear all entities."""
        pass


class IMemoryManager(ABC):
    """Interface for memory manager with extraction and persistence."""

    @abstractmethod
    def auto_extract(self, text: str):
        """Extract entities from text and store suggestions."""
        pass

    @abstractmethod
    def cleanup(self):
        """Clean up old/low-confidence entries."""
        pass

    @abstractmethod
    def export(self, export_path):
        """Export memory to file."""
        pass

    @abstractmethod
    def get_all_facts(self) -> Dict[str, Dict[str, Any]]:
        """Get all facts from facts table."""
        pass

    @abstractmethod
    def set_secret(self, key: str, value: str):
        """Store a secret encrypted."""
        pass

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve and decrypt a secret."""
        pass
