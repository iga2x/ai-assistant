"""Tool name resolution and deprecation handling."""

from typing import Optional
from assistant.tools.models import logger


class Resolver:
    """Resolves tool names, handles aliases and deprecation."""

    ALIASES = {
        "netcat": "nc",
        "ncat": "nc",
    }

    REPLACEMENTS = {
        "subjack": "subzy",  # deprecated → replacement
    }

    DEPRECATED = {
        "subjack": "Deprecated, use subzy instead",
        "wifitex": "Custom tool, remove - not maintained",
    }

    BAD_VERSION_CMDS = {
        "assetfinder": ["--help"],  # doesn't support --version
        "john": ["--list=build-info"],
        "autopsy": ["-h"],
        "dirsearch": ["--help"],
    }

    def resolve(self, name: str) -> Optional[str]:
        """Resolve tool name with alias and deprecation handling.

        Args:
            name: Original tool name

        Returns:
            Resolved tool name or None if deprecated without replacement
        """
        name_lower = name.lower()

        # Check if deprecated
        if name_lower in self.DEPRECATED:
            replacement = self.REPLACEMENTS.get(name_lower)
            if replacement:
                logger.warning(f"{name} deprecated, using {replacement}")
                return replacement
            else:
                logger.error(f"{name} deprecated, no replacement available: {self.DEPRECATED[name_lower]}")
                return None

        # Check for alias
        if name_lower in self.ALIASES:
            logger.info(f"{name} is alias for {self.ALIASES[name_lower]}")
            return self.ALIASES[name_lower]

        return name

    def get_version_flags(self, name: str, default_flags: list) -> list:
        """Get version flags, with overrides for problematic tools.

        Args:
            name: Tool name
            default_flags: Default version flags to use

        Returns:
            List of version flags to try
        """
        name_lower = name.lower()
        if name_lower in self.BAD_VERSION_CMDS:
            return self.BAD_VERSION_CMDS[name_lower]
        return default_flags

    def is_deprecated(self, name: str) -> bool:
        """Check if tool is deprecated.

        Args:
            name: Tool name

        Returns:
            True if deprecated
        """
        return name.lower() in self.DEPRECATED

    def get_replacement(self, name: str) -> Optional[str]:
        """Get replacement for deprecated tool.

        Args:
            name: Deprecated tool name

        Returns:
            Replacement tool name or None
        """
        return self.REPLACEMENTS.get(name.lower())
