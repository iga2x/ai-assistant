"""Central API for tool management - orchestrates detection, installation, updates.

DEPRECATED: Use ToolRegistry from assistant.tools.registry for tool discovery and execution.
This class is now only for lifecycle operations (install/uninstall/update).

MIGRATION GUIDE:
- For tool discovery: Use ToolRegistry.get_global_registry().detect()
- For tool execution: Use ToolRegistry.get_global_registry().execute()
- For installation: Still use ToolManager (this class)

ARCHITECTURE (Issue 14 Fix):
1. detector.py: Low-level detection (internal use only)
2. registry.py: MAIN INTERFACE - tool discovery and execution
3. manager.py: Lifecycle operations (install/uninstall/update) - this file
"""

import os
import json
import time
import shutil
import threading
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from assistant.tools.models import (
    ToolInfo, ToolStatus, Result, ErrorCode, InstallPlan,
    DependencyCheck, ProgressCallback, CriticalErrorSet,
    RetryableErrorSet, logger
)
from assistant.tools.detector import detect_tool
from assistant.tools.installer import (
    install_tool, update_tool, install_with_retry
)
from assistant.tools.resolver import Resolver


class ToolManager:
    """Central API for tool management operations."""

    # High-risk tools that always require explicit approval
    HIGH_RISK_TOOLS = {"metasploit", "sqlmap", "hydra", "exploitdb"}

    def __init__(self, cache_ttl: int = 300, custom_tools_path: str = None):
        """Initialize tool manager.

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 300 = 5 minutes)
            custom_tools_path: Path to custom_tools.yaml (default: ~/.assistant/custom_tools.yaml)
        """
        # Load metadata
        self.core_tools = self._load_core_metadata()
        self.custom_tools = self._load_custom_tools(custom_tools_path)

        # Initialize components
        self.resolver = Resolver()

        # Concurrency control - SEPARATE LOCKS to prevent deadlock
        self._install_lock = threading.Lock()
        self._cache_lock = threading.Lock()

        # Persistent state
        self._cache_path = os.path.expanduser("~/.assistant/cache/tools.json")
        self._cache_ttl = cache_ttl
        self._failed_installs_path = os.path.expanduser("~/.assistant/cache/failed_installs.json")

        # Ensure cache directories exist
        os.makedirs(os.path.dirname(self._cache_path), exist_ok=True)
        os.makedirs(os.path.dirname(self._failed_installs_path), exist_ok=True)

        # Initialize Registry
        from assistant.tools.registry import get_global_registry
        self.registry = get_global_registry()

        logger.info("ToolManager initialized")

    def _load_core_metadata(self) -> Dict[str, Dict]:
        """Load core tool metadata from metadata.py."""
        from assistant.tools.metadata import CORE_TOOLS
        return CORE_TOOLS

    def _load_custom_tools(self, custom_tools_path: str = None) -> Dict[str, Dict]:
        """Load and validate custom tools from YAML."""
        if custom_tools_path is None:
            custom_tools_path = os.path.expanduser("~/.assistant/custom_tools.yaml")

        if not os.path.exists(custom_tools_path):
            return {}

        try:
            with open(custom_tools_path, 'r') as f:
                data = yaml.safe_load(f)

            if not data or 'tools' not in data:
                logger.warning(f"No tools found in {custom_tools_path}")
                return {}

            validated = {}
            for name, metadata in data['tools'].items():
                if self._validate_tool_metadata(name, metadata):
                    validated[name] = metadata
                else:
                    logger.warning(f"Validation failed for tool: {name}")
            
            return validated
        except Exception as e:
            logger.error(f"Error loading custom_tools.yaml from {custom_tools_path}: {e}")
            return {}

    def _validate_tool_metadata(self, name: str, metadata: Dict) -> bool:
        """Validate tool metadata has required fields."""
        required_fields = ["name", "ecosystem", "install_cmd", "version_flags"]
        for field in required_fields:
            if field not in metadata:
                return False
        return True

    def detect(self, use_cache: bool = True, progress_callback: ProgressCallback = None) -> List[ToolInfo]:
        """Load metadata, call detector, return results. Never mutates metadata."""
        # Delegate to unified registry
        return self.registry.list_all(use_cache=use_cache)

    def is_available(self, tool_name: str) -> bool:
        """Check if tool is installed and available."""
        return self.registry.is_available(tool_name)

    def list_available(self) -> List[Dict[str, Any]]:
        """List all available tools with their status."""
        detected = self.registry.list_all(use_cache=True)
        return [t.to_dict() for t in detected]

    def get_missing(self, category: str = None) -> List[Dict[str, Any]]:
        """Get tools that are not installed."""
        detected = self.detect()
        missing = [t for t in detected if not t.is_available()]
        if category:
            missing = [t for t in missing if t.category == category]
        return [t.to_dict() for t in missing]

    def create_install_plan_for_tools(self, tool_names: List[str]) -> InstallPlan:
        """Create install plan for specific tools."""
        filtered = []
        for name in tool_names:
            metadata = self._get_tool_metadata(name)
            if metadata:
                resolved = self.resolver.resolve(name) or name
                metadata_copy = dict(metadata)
                metadata_copy["name"] = resolved
                filtered.append(metadata_copy)
        
        return self._create_install_plan(filtered)

    def _create_install_plan(self, tools: List[Dict]) -> InstallPlan:
        """Create install plan from tool list."""
        runtime_tools = []
        categories = set()

        for tool in tools:
            runtime_tool = dict(tool)
            deps = self._check_dependencies(runtime_tool)
            runtime_tool["dependencies_ok"] = deps.available
            runtime_tool["dependency_hint"] = deps.hint
            runtime_tool["installer_hint"] = deps.installer_hint
            runtime_tools.append(runtime_tool)
            categories.add(tool.get("category", "unknown"))

        grouped = {}
        for t in runtime_tools:
            ecosystem = t.get("ecosystem", "unknown")
            if ecosystem not in grouped:
                grouped[ecosystem] = []
            grouped[ecosystem].append(t)

        return InstallPlan(
            tools=grouped,
            total=len(runtime_tools),
            categories=list(categories)
        )

    def update_tool(self, tool_name: str, dry_run: bool = False) -> Result:
        """Update a single tool."""
        metadata = self._get_tool_metadata(tool_name)
        if not metadata:
            return Result(success=False, code=ErrorCode.NOT_FOUND, message=f"Tool {tool_name} not found")

        with self._install_lock:
            result = update_tool(metadata, dry_run=dry_run)
            if result.success and not dry_run:
                self._clear_cache()
            return result

    def _get_tool_metadata(self, tool_name: str) -> Optional[Dict]:
        """Get tool metadata from core or custom."""
        tool_name_lower = tool_name.lower()
        for name, metadata in self.custom_tools.items():
            if name.lower() == tool_name_lower:
                return dict(metadata)
        for name, metadata in self.core_tools.items():
            if name.lower() == tool_name_lower:
                return dict(metadata)
        return None

    def _check_dependencies(self, tool: Dict) -> DependencyCheck:
        """Check if tool dependencies are met."""
        ecosystem = tool.get("ecosystem")
        if ecosystem == "go" and not shutil.which("go"):
            return DependencyCheck(available=False, missing=["go"], hint="Go is required", installer_hint="sudo apt install golang")
        if ecosystem == "cargo" and not shutil.which("cargo"):
            return DependencyCheck(available=False, missing=["cargo"], hint="Rust/Cargo is required", installer_hint="curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh")
        return DependencyCheck(available=True)

    def _is_high_risk(self, tool: Dict) -> bool:
        """Check if tool is considered high risk."""
        return tool.get("name") in self.HIGH_RISK_TOOLS or tool.get("risk") == "high"

    def _save_cache(self, detected: List[ToolInfo]):
        """Save detection results to cache."""
        with self._cache_lock:
            try:
                data = {
                    "timestamp": time.time(),
                    "tools": [t.to_dict() for t in detected]
                }
                with open(self._cache_path, 'w') as f:
                    json.dump(data, f)
            except Exception as e:
                logger.error(f"Failed to save cache: {e}")

    def _load_cache(self) -> Optional[List[ToolInfo]]:
        """Load detection results from cache."""
        with self._cache_lock:
            try:
                if not os.path.exists(self._cache_path):
                    return None
                with open(self._cache_path, 'r') as f:
                    data = json.load(f)
                
                if time.time() - data["timestamp"] > self._cache_ttl:
                    return None
                
                loaded_tools = []
                for t in data["tools"]:
                    # Convert status string back to Enum
                    if "status" in t and isinstance(t["status"], str):
                        t["status"] = ToolStatus(t["status"])
                    loaded_tools.append(ToolInfo(**t))
                return loaded_tools
            except Exception:
                return None

    def _clear_cache(self):
        """Clear detection cache."""
        with self._cache_lock:
            if os.path.exists(self._cache_path):
                os.remove(self._cache_path)

    def _record_failed_install(self, tool_name: str, result: Result):
        """Record a failed installation attempt."""
        try:
            failed = self._get_failed_installs()
            entry = failed.get(tool_name, {"attempts": 0, "last_error": ""})
            entry["attempts"] += 1
            entry["last_error"] = result.message
            entry["retry_count"] = entry.get("retry_count", 0) + 1
            entry["message"] = result.message
            failed[tool_name] = entry
            with open(self._failed_installs_path, 'w') as f:
                json.dump(failed, f)
        except Exception:
            pass

    def _get_failed_installs(self) -> Dict:
        """Get history of failed installations."""
        try:
            if not os.path.exists(self._failed_installs_path):
                return {}
            with open(self._failed_installs_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
