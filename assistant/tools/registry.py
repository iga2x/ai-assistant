"""Tool registry - MAIN INTERFACE for tool discovery and execution (Issue 14 Fix).

This is the SINGLE source of truth for tool operations:
- Tool discovery and availability checking
- Tool metadata and capabilities
- Tool execution

ARCHITECTURE (Issue 14 Fix):
1. detector.py: Low-level detection (internal use by registry)
2. registry.py: MAIN INTERFACE - use this for discovery and execution
3. manager.py: Lifecycle operations (install/uninstall/update) - use ToolManager

USAGE:
    registry = ToolRegistry.get_global_registry()
    result = registry.detect()  # Find available tools
    result = registry.execute("nmap", "scan 192.168.1.1")  # Run tool
"""

import shutil
from typing import Dict, List, Optional, Any
from assistant.tools.models import (
    ToolInfo, ToolStatus, Result, logger
)
from assistant.tools.detector import detect_tool
from assistant.tools.metadata import CORE_TOOLS
from assistant.tools.runner import ToolRunner


class ToolRegistry:
    """Central registry for tool discovery, metadata, and execution.

    This is the SINGLE source of truth for:
    - What tools exist
    - What tools are available
    - Tool metadata and capabilities
    - Tool execution
    """

    def __init__(self, config: Optional[Any] = None):
        """Initialize tool registry.

        Args:
            config: Optional config for timeout settings
        """
        from assistant.tools.resolver import Resolver
        self.config = config
        self.metadata = CORE_TOOLS
        self.resolver = Resolver()
        self.runner = ToolRunner()
        self._cache: Dict[str, ToolInfo] = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_time = 0

    def is_available(self, tool_name: str, use_cache: bool = True) -> bool:
        """Check if tool is available."""
        if tool_name == "shell":
            return True
        resolved = self.resolver.resolve(tool_name)

        if not resolved:
            return False
        tool_info = self.get_tool_info(resolved, use_cache)
        return tool_info.is_available() if tool_info else False

    def get_tool_info(self, tool_name: str, use_cache: bool = True) -> Optional[ToolInfo]:
        """Get detailed information about a tool.

        Args:
            tool_name: Name of tool to query
            use_cache: Use cached detection results

        Returns:
            ToolInfo or None if tool not found
        """
        resolved = self.resolver.resolve(tool_name)
        if not resolved:
            return None

        # Check cache first
        if use_cache and resolved in self._cache:
            return self._cache[resolved]

        # Find metadata
        metadata = self._find_tool_metadata(resolved)
        if not metadata:
            return None

        # Create runtime copy for detector
        runtime_metadata = dict(metadata)
        runtime_metadata["name"] = resolved
        
        # Override version flags if needed
        runtime_metadata["version_flags"] = self.resolver.get_version_flags(
            resolved, 
            runtime_metadata.get("version_flags", ["--version"])
        )

        # Detect tool
        tool_info = detect_tool(runtime_metadata)

        # Cache result
        if use_cache:
            self._cache[resolved] = tool_info

        return tool_info

    def list_available(self, use_cache: bool = True) -> List[ToolInfo]:
        """List all available tools.

        Args:
            use_cache: Use cached detection results

        Returns:
            List of ToolInfo for all available tools
        """
        available = []
        for tool_name in self.metadata.keys():
            info = self.get_tool_info(tool_name, use_cache)
            if info and info.is_available():
                available.append(info)
        return available

    def list_all(self, use_cache: bool = True) -> List[ToolInfo]:
        """List all tools (available and unavailable).

        Args:
            use_cache: Use cached detection results

        Returns:
            List of ToolInfo for all known tools
        """
        all_tools = []
        for tool_name in self.metadata.keys():
            info = self.get_tool_info(tool_name, use_cache)
            if info:
                all_tools.append(info)
        return all_tools

    def get_missing(self, category: str = None, use_cache: bool = True) -> List[ToolInfo]:
        """Get tools that are not installed.

        Args:
            category: Filter by category (optional)
            use_cache: Use cached detection results

        Returns:
            List of ToolInfo for missing tools
        """
        missing = []
        for tool_name, metadata in self.metadata.items():
            if category and metadata.get('category') != category:
                continue

            info = self.get_tool_info(tool_name, use_cache)
            if info and not info.is_available():
                missing.append(info)
        return missing

    def run_tool(self, tool_name: str, args: str, cwd: str = None) -> Dict[str, Any]:
        """Execute a tool.

        This is the PRIMARY method for tool execution. All tool execution
        should go through this method.

        Args:
            tool_name: Name of tool to run
            args: Arguments to pass to tool
            cwd: Working directory for execution

        Returns:
            Execution result dict
        """
        # Check if tool is available first
        if not self.is_available(tool_name):
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Tool {tool_name} is not available',
                'returncode': -1
            }

        # Execute via ToolRunner
        result = self.runner.run_tool(tool_name, args, cwd=cwd)
        return result

    def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a tool.

        Args:
            tool_name: Name of tool

        Returns:
            Metadata dict or None if not found
        """
        return self._find_tool_metadata(tool_name)

    def clear_cache(self):
        """Clear the detection cache."""
        self._cache.clear()
        self._last_cache_time = 0
        logger.info("Tool registry cache cleared")

    def refresh(self) -> None:
        """Refresh all tool detection results.

        Forces re-detection of all tools by clearing cache.
        """
        self.clear_cache()
        # Trigger detection of all tools
        for tool_name in self.metadata.keys():
            self.get_tool_info(tool_name, use_cache=False)
        logger.info("Tool registry refreshed")

    def _find_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Find metadata for a tool by name, resolving aliases."""
        resolved = self.resolver.resolve(tool_name)
        if not resolved:
            return None

        if resolved in self.metadata:
            return dict(self.metadata[resolved])
            
        return None


    def get_timeout(self, tool_name: str) -> int:
        """Get timeout for a specific tool.

        Args:
            tool_name: Name of tool

        Returns:
            Timeout in seconds
        """
        if self.config and hasattr(self.config, 'timeout'):
            tool_timeouts = self.config.timeout.tool
            if tool_name in tool_timeouts:
                return tool_timeouts[tool_name]
            return self.config.timeout.shell_command
        return 300  # Default 5 minutes


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_global_registry(config: Optional[Any] = None) -> ToolRegistry:
    """Get the global tool registry instance.

    Args:
        config: Optional config for timeout settings

    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry(config)
    return _global_registry
