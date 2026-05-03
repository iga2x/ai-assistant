"""AI tool selection logic for choosing the best tool for a specific task."""

import logging
from typing import Dict, List, Optional, Any
from assistant.tools.models import logger

class ToolSelector:
    """Selects best tool based on capability, priority, speed, and accuracy."""

    CAPABILITY_MAP = {
        "port_scan": {
            "nmap": {"priority": 10, "speed": "medium", "accuracy": "high"},
            "masscan": {"priority": 8, "speed": "fast", "accuracy": "medium"},
            "rustscan": {"priority": 7, "speed": "fast", "accuracy": "medium"}
        },
        "subdomain_enum": {
            "subfinder": {"priority": 10, "speed": "fast", "accuracy": "high"},
            "amass": {"priority": 9, "speed": "slow", "accuracy": "very_high"},
            "assetfinder": {"priority": 6, "speed": "fast", "accuracy": "medium"}
        },
        "vuln_scan": {
            "nuclei": {"priority": 10, "speed": "fast", "accuracy": "high"},
            "nikto": {"priority": 7, "speed": "medium", "accuracy": "medium"}
        },
        "web_fuzzing": {
            "ffuf": {"priority": 10, "speed": "fast", "accuracy": "high"},
            "gobuster": {"priority": 8, "speed": "medium", "accuracy": "high"},
            "dirsearch": {"priority": 6, "speed": "medium", "accuracy": "medium"}
        },
        "sql_injection": {
            "sqlmap": {"priority": 10, "speed": "medium", "accuracy": "high"}
        },
        "password_cracking": {
            "john": {"priority": 9, "speed": "medium", "accuracy": "high"},
            "hashcat": {"priority": 10, "speed": "fast", "accuracy": "high"},
            "hydra": {"priority": 8, "speed": "medium", "accuracy": "medium"}
        },
        "wifi_auditing": {
            "aircrack-ng": {"priority": 10, "speed": "medium", "accuracy": "high"},
            "wifite": {"priority": 9, "speed": "medium", "accuracy": "high"},
            "reaver": {"priority": 6, "speed": "slow", "accuracy": "medium"}
        },
        "memory_forensics": {
            "volatility3": {"priority": 10, "speed": "medium", "accuracy": "high"},
            "volatility": {"priority": 8, "speed": "medium", "accuracy": "high"}
        },
    }

    def __init__(self, manager):
        """Initialize ToolSelector.

        Args:
            manager: ToolManager instance for checking availability
        """
        self.manager = manager
        self.capability_map = self.CAPABILITY_MAP

    def select_best_tool(self, capability: str, preference: str = "balanced") -> Optional[str]:
        """Select best tool for a capability based on preference."""
        if capability not in self.capability_map:
            logger.warning(f"Unknown capability: {capability}")
            return None

        tools = self.capability_map[capability]
        available = [t for t in tools.keys() if self.manager.is_available(t)]

        if not available:
            logger.info(f"No available tools for capability: {capability}")
            return None

        if preference == "speed":
            speed_order = {"fast": 3, "medium": 2, "slow": 1}
            return max(available, key=lambda t: speed_order.get(tools[t]["speed"], 0))

        elif preference == "accuracy":
            accuracy_order = {"very_high": 3, "high": 2, "medium": 1}
            return max(available, key=lambda t: accuracy_order.get(tools[t]["accuracy"], 0))

        else:  # balanced
            return max(available, key=lambda t: tools[t]["priority"])

    def get_tools_by_capability(self, capability: str) -> List[str]:
        """Get all available tools for a capability."""
        if capability not in self.capability_map:
            return []
        return [t for t in self.capability_map[capability].keys()
                if self.manager.is_available(t)]

    def get_missing_tools_for_capability(self, capability: str) -> List[str]:
        """Get missing tools for a capability."""
        if capability not in self.capability_map:
            return []
        return [t for t in self.capability_map[capability].keys()
                if not self.manager.is_available(t)]
