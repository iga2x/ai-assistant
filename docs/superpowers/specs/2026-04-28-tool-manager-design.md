# Tool Management System Design

**Date:** 2026-04-28
**Status:** Design Complete (v3 - Final)
**Priority:** High

## Overview

Intelligent tool management system for AI assistant. Automates detection, installation, and lifecycle management of security tools with proper safety guards, error handling, and user approval flows.

## Problem Statement

Current tool system has critical flaws:
- Wrong version detection commands (assetfinder, john, autopsy)
- Missing ecosystem metadata (apt, go, pip, cargo, binary)
- No automated installation capability
- Confuses "not detected" with "not installed"
- No dependency checking
- No safety guards for offensive tools
- Hard-coded metadata in detector.py (should be pure)
- No version constraints or compatibility checking
- No update mechanism
- No tool location awareness
- No install lock / concurrency control
- No persistent state / cache
- Static capability mapping

## Solution

Four-layer architecture with separation of concerns, structured error handling, and AI integration with approval guards.

---

## Architecture

### Four Layers

**Layer 0 - Data (Immutable)**
- `metadata.py` - CORE_TOOLS catalog (80-100 curated security tools)
- `custom_tools.yaml` - User additions (editable)
- `resolver.py` - Aliases, replacements, deprecated tools, bad entries

**Layer 1 - Detection (Read-Only, Pure)**
- `detector.py` - Detection engine
- `detect_tool(metadata)` → ToolInfo
- `detect_tools(metadata_list)` → List[ToolInfo]
- `get_tool_version(version_flags)` → str
- **Never performs installs, never writes**

**Layer 2 - Management (Orchestrator)**
- `manager.py` - ToolManager class
- Central API: detect(), list(), get_missing(), create_install_plan()
- Loads metadata (Layer 0)
- Calls detector (Layer 1)
- Calls resolver (Layer 0)
- Calls installer (Layer 3) **ONLY after approval**

**Layer 3 - Installation (Write)**
- `installer.py` - Ecosystem installers
- apt, go, pip/pipx, cargo, binary, manual-note
- Sudo handling, dependency checking
- **Never called from detector.py**

### File Structure

```
assistant/tools/
├── models.py            # Shared dataclasses: Result, ToolInfo, DependencyCheck, InstallPlan, ErrorCode, ToolStatus
├── metadata.py          # CORE_TOOLS (data)
├── custom_tools.yaml    # User tools (data)
├── resolver.py          # Aliases/replacements (data transforms)
├── detector.py          # Pure detection (logic only)
├── installer.py         # Installation (logic only)
├── manager.py           # Central API (orchestrator)
└── [existing tool wrappers unchanged]
```

### Key Constraints

1. **Detector purity:** `detector.py` never calls `installer.py`
2. **Approval required:** All installs go through `manager.py` approval flow
3. **Metadata separation:** `CORE_TOOLS` in `metadata.py`, not `detector.py`
4. **Immutability:** Never mutate tool metadata inside functions

### Architectural Evolution

The current design provides a solid foundation. Future evolution toward a three-layer architecture:

**Current:** ToolManager (combined operations and selection)

**Future:**
- **ToolRegistry** - Pure data management (load, save, validate metadata)
- **ToolManager** - Operations (install, update, detect, cache)
- **ToolSelector** - AI decision layer (intelligent tool selection based on requirements)

This separation will enable:
- Easier testing of each component
- Pluggable selection strategies
- Better separation of data, operations, and AI logic

---

## Shared Models

### models.py - Dataclasses and Enums

```python
"""Shared data models for tool management system."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import json

# Setup logging
logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Structured error codes for tool operations."""
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    INSTALL_FAILED = "install_failed"
    UPDATE_FAILED = "update_failed"
    DEPENDENCY_MISSING = "dependency_missing"
    NETWORK_ERROR = "network_error"
    NOT_IN_PATH = "not_in_path"
    BROKEN = "broken"
    VALIDATION_ERROR = "validation_error"


class ToolStatus(Enum):
    """Tool installation and availability status."""
    INSTALLED = "installed"
    NOT_FOUND = "not_found"
    NOT_IN_PATH = "not_in_path"
    PERMISSION_DENIED = "permission_denied"
    BROKEN = "broken"
    OUTDATED = "outdated"


class CriticalErrorSet:
    """Errors that should stop batch operations."""
    CRITICAL = {
        ErrorCode.PERMISSION_DENIED,
        ErrorCode.DEPENDENCY_MISSING,
        ErrorCode.NOT_FOUND,
    }


class RetryableErrorSet:
    """Errors that should be retried."""
    RETRYABLE = {
        ErrorCode.TIMEOUT,
        ErrorCode.NETWORK_ERROR,
    }


@dataclass
class Result:
    """Result of a tool operation (install, update, detect)."""
    success: bool
    code: Optional[ErrorCode] = None
    message: str = ""
    stderr: str = ""
    hint: str = ""
    stage: str = ""  # detect, install, update, validate, etc.
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "success": self.success,
            "code": self.code.value if self.code else None,
            "message": self.message,
            "stderr": self.stderr,
            "hint": self.hint,
            "stage": self.stage,
            "context": self.context
        }


@dataclass
class ToolInfo:
    """Information about a detected tool."""
    name: str
    status: ToolStatus
    version: str = "unknown"
    path: str = ""
    category: str = ""
    error: str = ""
    hint: str = ""
    warning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "version": self.version,
            "path": self.path,
            "category": self.category,
            "error": self.error,
            "hint": self.hint,
            "warning": self.warning
        }

    def is_available(self) -> bool:
        """Check if tool is available for use."""
        return self.status in [ToolStatus.INSTALLED, ToolStatus.OUTDATED]


@dataclass
class DependencyCheck:
    """Result of dependency checking for a tool."""
    available: bool
    missing: List[str] = field(default_factory=list)
    hint: str = ""
    installer_hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "available": self.available,
            "missing": self.missing,
            "hint": self.hint,
            "installer_hint": self.installer_hint
        }


@dataclass
class InstallPlan:
    """Plan for tool installation."""
    tools: Dict[str, List[Dict]]  # ecosystem -> list of tools with runtime metadata
    total: int
    categories: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "tools": self.tools,
            "total": self.total,
            "categories": self.categories
        }


# Progress callback type
ProgressCallback = Callable[[str, int, int], None]  # message, current, total


def tool_info_to_dict(info: ToolInfo) -> Dict[str, Any]:
    """Helper to convert ToolInfo to dict. Use for API responses."""
    return info.to_dict()


def result_to_dict(result: Result) -> Dict[str, Any]:
    """Helper to convert Result to dict. Use for API responses."""
    return result.to_dict()
```

### Dependencies

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.8"
pydantic = "^2.0"
packaging = "^21.0"  # For version comparison
pyyaml = "^6.0"

[tool.poetry.dev-dependencies]
pytest = "^7.0"
pytest-cov = "^4.0"
```

---

## Components & Data Flow

### Component 1: metadata.py (Data Layer)

```python
"""Core tool metadata catalog."""

from typing import Dict, Any
from assistant.tools.models import logger

CORE_TOOLS = {
    "nmap": {
        "name": "nmap",
        "binary": "nmap",  # defaults to name if not specified
        "ecosystem": "apt",
        "install_cmd": "apt install nmap",
        "version_flags": ["--version", "-V"],
        "version_required": ">=7.0.0",
        "category": "scanner",
        "risk": "medium",
        "alternatives": [],
        "docs_url": "https://nmap.org/book/man.html",
        "deprecated": False,
        "priority": 10,
        "speed": "medium",
        "accuracy": "high"
    },
    "nuclei": {
        "name": "nuclei",
        "binary": "nuclei",
        "ecosystem": "go",
        "install_cmd": "go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
        "version_flags": ["-version"],
        "version_required": ">=3.0.0",
        "category": "scanner",
        "risk": "high",
        "alternatives": [],
        "docs_url": "https://github.com/projectdiscovery/nuclei",
        "deprecated": False,
        "priority": 9,
        "speed": "fast",
        "accuracy": "high"
    },
    # ... 80-100 curated tools
}
```

**Fields:**
- **Required:** `name`, `ecosystem`, `install_cmd`, `version_flags`, `version_required`
- **Optional:** `binary`, `category`, `risk`, `alternatives`, `docs_url`, `deprecated`, `priority`, `speed`, `accuracy`

### Component 2: custom_tools.yaml (User Data)

```yaml
tools:
  my-custom-tool:
    name: "my-custom-tool"
    ecosystem: "binary"
    install_cmd: "cp /path/to/tool /usr/local/bin/"
    version_flags: ["--version"]
    category: "custom"
    risk: "low"
    alternatives: []
    docs_url: ""
    deprecated: false
```

### Component 3: resolver.py (Data Transforms)

```python
ALIASES = {"netcat": "nc"}
REPLACEMENTS = {
    "subjack": "subzy"  # deprecated → replacement
}
DEPRECATED = {
    "wifitex": "Custom tool, remove"
}
BAD_VERSION_CMDS = {
    "assetfinder": ["--help"],  # doesn't support --version
    "john": ["--list=build-info"],
    "autopsy": ["-h"],
    "dirsearch": ["--help"],
}
```

### Component 4: detector.py (Pure Detection)

```python
"""Pure detection engine - no side effects, no installs, no metadata mutation."""

import shutil
import subprocess
import re
from typing import Dict, List, Optional
from packaging.version import parse as parse_version
from packaging.specifiers import SpecifierSet

from assistant.tools.models import (
    ToolInfo, ToolStatus, ErrorCode, Result, logger
)


def detect_tool(metadata: Dict) -> ToolInfo:
    """Pure function. No side effects. No installs. Never mutates metadata."""
    try:
        binary = metadata.get("binary", metadata["name"])
        path = shutil.which(binary)

        if not path:
            return ToolInfo(
                name=metadata["name"],
                status=ToolStatus.NOT_FOUND,
                category=metadata.get("category", "unknown")
            )

        version = get_tool_version(binary, metadata["version_flags"])

        # Check if version meets requirements
        status = ToolStatus.INSTALLED
        warning = ""

        if version != "unknown" and "version_required" in metadata:
            if not _meets_version_requirement(version, metadata["version_required"]):
                status = ToolStatus.OUTDATED
                warning = f"Version {version} does not meet requirement {metadata['version_required']}"

        return ToolInfo(
            name=metadata["name"],
            status=status,
            version=version,
            path=path,
            category=metadata.get("category", "unknown"),
            warning=warning
        )

    except PermissionError as e:
        return ToolInfo(
            name=metadata["name"],
            status=ToolStatus.PERMISSION_DENIED,
            category=metadata.get("category", "unknown"),
            error="Permission denied",
            hint="Check file permissions"
        )
    except Exception as e:
        logger.error(f"Error detecting tool {metadata.get('name', 'unknown')}: {e}")
        return ToolInfo(
            name=metadata["name"],
            status=ToolStatus.BROKEN,
            category=metadata.get("category", "unknown"),
            error=f"Detection error: {str(e)}",
            hint="Tool may be corrupted or misconfigured"
        )


def get_tool_version(binary: str, version_flags: List[str]) -> str:
    """Try multiple version flags in order."""
    for flag in version_flags:
        try:
            result = subprocess.run(
                [binary, flag],
                capture_output=True,
                timeout=2.0
            )
            if result.returncode == 0:
                return parse_version_output(result.stdout.decode(), result.stderr.decode())
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            continue
        except Exception as e:
            logger.warning(f"Error checking version for {binary} with flag {flag}: {e}")
            continue
    return "unknown"


def parse_version_output(stdout: str, stderr: str) -> str:
    """Parse version string from tool output."""
    # Try stdout first
    version = _extract_version(stdout)
    if version != "unknown":
        return version

    # Fallback to stderr
    version = _extract_version(stderr)
    return version


def _extract_version(text: str) -> str:
    """Extract version number from text using regex."""
    # Common version patterns
    patterns = [
        r'\b(\d+\.\d+[\d.]*)\b',  # 7.95, 3.2.4, etc.
        r'v(\d+\.\d+[\d.]*)',     # v7.95, v3.2.4
        r'Version:\s*(\d+\.\d+[\d.]*)',  # Version: 7.95
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return "unknown"


def _meets_version_requirement(current: str, required: str) -> bool:
    """Check if current version meets requirement (e.g., '>=3.0.0')."""
    try:
        if current == "unknown" or not current:
            return False

        spec = SpecifierSet(required)
        return parse_version(current) in spec
    except Exception as e:
        logger.warning(f"Failed to compare versions: current={current}, required={required}, error={e}")
        return False
```

### Component 5: installer.py (Install Handlers)

```python
"""Ecosystem-specific installers and updaters."""

import shutil
import subprocess
from typing import Dict, Optional

from assistant.tools.models import (
    Result, ErrorCode, CriticalErrorSet, RetryableErrorSet,
    DependencyCheck, logger
)


def install_tool(tool: Dict, dry_run: bool = False, progress_callback=None) -> Result:
    """Install one tool. Called ONLY by manager.py.

    Args:
        tool: Tool metadata dict
        dry_run: If True, only return what would be done
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
    if dry_run:
        return Result(
            success=True,
            message=f"Dry run: would install {tool['name']} via {tool['ecosystem']}",
            hint=f"Command: {tool['install_cmd']}"
        )

    ecosystem = tool["ecosystem"]

    if progress_callback:
        progress_callback(f"Starting installation of {tool['name']}...", 0, 1)

    if ecosystem == "apt":
        return install_apt(tool, sudo=True, progress_callback=progress_callback)
    elif ecosystem == "go":
        return install_go(tool, progress_callback=progress_callback)
    elif ecosystem == "pip":
        return install_pip(tool, progress_callback=progress_callback)
    elif ecosystem == "cargo":
        return install_cargo(tool, progress_callback=progress_callback)
    elif ecosystem == "binary":
        return install_binary(tool, progress_callback=progress_callback)
    elif ecosystem == "manual-note":
        return show_manual_instructions(tool)
    else:
        return Result(
            success=False,
            code=ErrorCode.NOT_FOUND,
            message=f"Unsupported ecosystem: {ecosystem}",
            hint=f"Tool {tool['name']} cannot be auto-installed",
            stage="install"
        )


def update_tool(tool: Dict, dry_run: bool = False, progress_callback=None) -> Result:
    """Update one tool to latest version."""
    if dry_run:
        return Result(
            success=True,
            message=f"Dry run: would update {tool['name']} via {tool['ecosystem']}",
            stage="update"
        )

    ecosystem = tool["ecosystem"]

    if ecosystem == "apt":
        return update_apt(tool, sudo=True, progress_callback=progress_callback)
    elif ecosystem == "go":
        return update_go(tool, progress_callback=progress_callback)
    elif ecosystem == "pip":
        return update_pip(tool, progress_callback=progress_callback)
    elif ecosystem == "cargo":
        return update_cargo(tool, progress_callback=progress_callback)
    else:
        return Result(
            success=False,
            code=ErrorCode.NOT_FOUND,
            message=f"Update not supported for ecosystem: {ecosystem}",
            hint=f"Tool {tool['name']} cannot be auto-updated",
            stage="update"
        )
    """Install one tool. Called ONLY by manager.py."""
    ecosystem = tool["ecosystem"]

    if ecosystem == "apt":
        return install_apt(tool, sudo=True)
    elif ecosystem == "go":
        return install_go(tool)
    elif ecosystem == "pip":
        return install_pip(tool)  # prefers pipx
    elif ecosystem == "cargo":
        return install_cargo(tool)
    elif ecosystem == "binary":
        return install_binary(tool)
    elif ecosystem == "manual-note":
        return show_manual_instructions(tool)

def update_tool(tool: Dict) -> Result:
    """Update one tool to latest version."""
    ecosystem = tool["ecosystem"]

    if ecosystem == "apt":
        return update_apt(tool, sudo=True)
    elif ecosystem == "go":
        return update_go(tool)
    elif ecosystem == "pip":
        return update_pip(tool)
    elif ecosystem == "cargo":
        return update_cargo(tool)
    else:
        return Result(
            success=False,
            code=ErrorCode.NOT_FOUND,
            message=f"Update not supported for ecosystem: {ecosystem}"
        )

def update_apt(tool: Dict, sudo: bool) -> Result:
    cmd = f"{'sudo ' if sudo else ''}apt upgrade -y {tool['name']}"
    result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

    if result.returncode != 0:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message="Update failed",
            stderr=result.stderr.decode(),
            hint="Check apt repository or run 'apt update'"
        )

    return Result(success=True)

def update_go(tool: Dict) -> Result:
    cmd = f"go install -v github.com/projectdiscovery/{tool['name']}/v3/cmd/{tool['name']}@latest"
    result = subprocess.run(cmd.split(), capture_output=True, timeout=600)

    if result.returncode != 0:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message="Go update failed",
            stderr=result.stderr.decode(),
            hint="Check Go installation and network connectivity"
        )

    return Result(success=True)

def update_pip(tool: Dict) -> Result:
    if shutil.which("pipx"):
        cmd = f"pipx upgrade {tool['name']}"
    else:
        cmd = f"pip3 install --upgrade --user {tool['name']}"

    result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

    if result.returncode != 0:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message="Pip update failed",
            stderr=result.stderr.decode(),
            hint="Check Python environment"
        )

    return Result(success=True)

def update_cargo(tool: Dict, progress_callback=None) -> Result:
    cmd = f"cargo install {tool['name']} --force"
    result = subprocess.run(cmd.split(), capture_output=True, timeout=600)

    if result.returncode != 0:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message="Cargo update failed",
            stderr=result.stderr.decode(),
            hint="Check Rust installation",
            stage="update"
        )

    return Result(success=True)

def install_apt(tool: Dict, sudo: bool, progress_callback=None) -> Result:
    cmd = f"{'sudo ' if sudo else ''}apt install -y {tool['name']}"

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

        if result.returncode != 0:
            stderr = result.stderr.decode()
            error_msg = "Install failed"

            if "Unable to locate package" in stderr:
                error_msg = f"Package {tool['name']} not found in repository"
            elif "Permission denied" in stderr:
                return Result(
                    success=False,
                    code=ErrorCode.PERMISSION_DENIED,
                    message="Permission denied",
                    stderr=stderr,
                    hint="Try running with sudo or as root",
                    stage="install"
                )

            return Result(
                success=False,
                code=ErrorCode.INSTALL_FAILED,
                message=error_msg,
                stderr=stderr,
                hint="Run 'apt update' and try again",
                stage="install"
            )

        return Result(success=True, stage="install")

    except subprocess.TimeoutExpired:
        return Result(
            success=False,
            code=ErrorCode.TIMEOUT,
            message="Installation timeout",
            hint="Network issue or large package",
            stage="install"
        )
    except PermissionError:
        return Result(
            success=False,
            code=ErrorCode.PERMISSION_DENIED,
            message="Permission denied",
            hint="Use sudo or run as root",
            stage="install"
        )
    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message=f"Unexpected error: {str(e)}",
            hint="Check system logs for details",
            stage="install"
        )


def install_go(tool: Dict, progress_callback=None) -> Result:
    """Install Go tool."""
    cmd = tool['install_cmd']

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=600)

        if result.returncode != 0:
            return Result(
                success=False,
                code=ErrorCode.INSTALL_FAILED,
                message="Go installation failed",
                stderr=result.stderr.decode(),
                hint="Check Go installation and network connectivity",
                stage="install"
            )

        # Check if ~/go/bin is in PATH
        import os
        go_bin = os.path.expanduser("~/go/bin")
        path_dirs = os.getenv('PATH', '').split(':')

        if go_bin not in path_dirs:
            return Result(
                success=True,
                message=f"{tool['name']} installed via Go",
                hint=f"⚠️  Add {go_bin} to PATH or run: export PATH=$PATH:{go_bin}",
                stage="install"
            )

        return Result(success=True, stage="install")

    except subprocess.TimeoutExpired:
        return Result(
            success=False,
            code=ErrorCode.TIMEOUT,
            message="Go installation timeout",
            hint="Network issue or large download",
            stage="install"
        )
    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message=f"Unexpected error: {str(e)}",
            hint="Check Go installation",
            stage="install"
        )


def install_pip(tool: Dict, progress_callback=None) -> Result:
    """Prefer pipx over system pip."""
    if shutil.which("pipx"):
        cmd = f"pipx install {tool['name']}"
        ecosystem = "pipx"
    else:
        cmd = f"pip3 install --user {tool['name']}"
        ecosystem = "pip"
        logger.warning(f"pipx not found, using system pip. Consider installing pipx for better isolation.")

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

        if result.returncode != 0:
            stderr = result.stderr.decode()
            return Result(
                success=False,
                code=ErrorCode.INSTALL_FAILED,
                message=f"{ecosystem} installation failed",
                stderr=stderr,
                hint="Check Python environment and pip configuration",
                stage="install"
            )

        # Check if ~/.local/bin is in PATH (for pip install --user)
        if ecosystem == "pip":
            local_bin = os.path.expanduser("~/.local/bin")
            path_dirs = os.getenv('PATH', '').split(':')

            if local_bin not in path_dirs:
                return Result(
                    success=True,
                    message=f"{tool['name']} installed via pip",
                    hint=f"⚠️  Add {local_bin} to PATH or run: export PATH=$PATH:{local_bin}",
                    stage="install"
                )

        return Result(success=True, stage="install")

    except subprocess.TimeoutExpired:
        return Result(
            success=False,
            code=ErrorCode.TIMEOUT,
            message="Pip installation timeout",
            hint="Network issue or large package",
            stage="install"
        )
    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message=f"Unexpected error: {str(e)}",
            hint="Check Python environment",
            stage="install"
        )


def install_cargo(tool: Dict, progress_callback=None) -> Result:
    """Install Rust tool via cargo."""
    cmd = f"cargo install {tool['name']}"

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=600)

        if result.returncode != 0:
            return Result(
                success=False,
                code=ErrorCode.INSTALL_FAILED,
                message="Cargo installation failed",
                stderr=result.stderr.decode(),
                hint="Check Rust installation and network connectivity",
                stage="install"
            )

        # Check if ~/.cargo/bin is in PATH
        import os
        cargo_bin = os.path.expanduser("~/.cargo/bin")
        path_dirs = os.getenv('PATH', '').split(':')

        if cargo_bin not in path_dirs:
            return Result(
                success=True,
                message=f"{tool['name']} installed via cargo",
                hint=f"⚠️  Add {cargo_bin} to PATH or run: export PATH=$PATH:{cargo_bin}",
                stage="install"
            )

        return Result(success=True, stage="install")

    except subprocess.TimeoutExpired:
        return Result(
            success=False,
            code=ErrorCode.TIMEOUT,
            message="Cargo installation timeout",
            hint="Network issue or large download",
            stage="install"
        )
    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message=f"Unexpected error: {str(e)}",
            hint="Check Rust installation",
            stage="install"
        )


def install_binary(tool: Dict, progress_callback=None) -> Result:
    """Install binary manually."""
    return Result(
        success=False,
        code=ErrorCode.NOT_FOUND,
        message=f"Binary installation not automated for {tool['name']}",
        hint=f"Manual installation required: {tool['install_cmd']}",
        stage="install"
    )


def show_manual_instructions(tool: Dict) -> Result:
    """Show manual installation instructions."""
    return Result(
        success=False,
        code=ErrorCode.NOT_FOUND,
        message=f"Manual installation required for {tool['name']}",
        hint=f"Install instructions: {tool.get('docs_url', tool['install_cmd'])}",
        stage="install"
    )


def install_with_retry(tool: Dict, max_attempts: int = 2, progress_callback=None) -> Result:
    """Install with retry for retryable errors."""
    for attempt in range(max_attempts):
        result = install_tool(tool, progress_callback=progress_callback)

        if result.success:
            return result

        if result.code not in RetryableErrorSet.RETRYABLE:
            break  # Don't retry non-retryable errors

        logger.info(f"Retryable error, attempt {attempt + 1}/{max_attempts}: {result.message}")

    return result
```

### Component 6: manager.py (Orchestrator)

```python
"""Central API for tool management - orchestrates detection, installation, updates."""

import os
import json
import time
import threading
import yaml
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
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
                logger.warning(f"Invalid custom_tools.yaml format")
                return {}

            # Validate each tool entry
            validated = {}
            for name, metadata in data['tools'].items():
                if self._validate_tool_metadata(name, metadata):
                    validated[name] = metadata
                else:
                    logger.warning(f"Invalid metadata for custom tool: {name}")

            logger.info(f"Loaded {len(validated)} custom tools")
            return validated

        except Exception as e:
            logger.error(f"Error loading custom_tools.yaml: {e}")
            return {}

    def _validate_tool_metadata(self, name: str, metadata: Dict) -> bool:
        """Validate tool metadata has required fields."""
        required_fields = ["name", "ecosystem", "install_cmd", "version_flags"]

        for field in required_fields:
            if field not in metadata:
                logger.error(f"Tool {name} missing required field: {field}")
                return False

        # Validate ecosystem
        valid_ecosystems = {"apt", "go", "pip", "cargo", "binary", "manual-note"}
        if metadata["ecosystem"] not in valid_ecosystems:
            logger.error(f"Tool {name} has invalid ecosystem: {metadata['ecosystem']}")
            return False

        return True

    def detect(self, use_cache: bool = True, progress_callback: ProgressCallback = None) -> List[ToolInfo]:
        """Load metadata, call detector, return results. Never mutates metadata.

        Args:
            use_cache: If True, use cached results if available
            progress_callback: Optional callback for progress updates

        Returns:
            List of ToolInfo for all tools
        """
        if use_cache:
            cached = self._load_cache()
            if cached:
                logger.info("Using cached tool detection results")
                return cached

        # Merge core and custom tools (custom takes precedence)
        all_tools = {**self.core_tools, **self.custom_tools}
        detected = []
        total = len(all_tools)

        for idx, (name, metadata) in enumerate(all_tools.items()):
            if progress_callback:
                progress_callback(f"Detecting {name}...", idx, total)

            resolved = self.resolver.resolve(name)
            if resolved is None:  # deprecated without replacement
                logger.info(f"Skipping deprecated tool: {name}")
                continue

            # Create runtime copy, never mutate original metadata
            runtime_metadata = dict(metadata)
            runtime_metadata["name"] = resolved
            detected.append(detect_tool(runtime_metadata))

        # Cache results
        self._save_cache(detected)

        logger.info(f"Detected {len(detected)} tools")
        return detected

    def get_missing(self, category: str = None) -> List[Dict[str, Any]]:
        """Filter uninstalled or outdated tools.

        Args:
            category: Optional category filter

        Returns:
            List of tool dicts that are missing
        """
        detected = self.detect()
        missing = [t for t in detected if t.status not in [ToolStatus.INSTALLED, ToolStatus.OUTDATED]]

        if category:
            missing = [t for t in missing if t.category == category]

        return [t.to_dict() for t in missing]

    def get_outdated(self) -> List[Dict[str, Any]]:
        """Get tools that are installed but don't meet version requirements."""
        detected = self.detect()
        outdated = [t for t in detected if t.status == ToolStatus.OUTDATED]
        return [t.to_dict() for t in outdated]

    def is_available(self, tool_name: str) -> bool:
        """Check if tool is installed and available.

        Args:
            tool_name: Name of tool to check (case-insensitive)

        Returns:
            True if tool is available for use
        """
        tool_name_lower = tool_name.lower()
        detected = self.detect()

        for tool in detected:
            if tool.name.lower() == tool_name_lower:
                return tool.is_available()

        return False

    def _get_tool_metadata(self, tool_name: str) -> Optional[Dict]:
        """Get tool metadata from core or custom. Custom takes precedence.

        Args:
            tool_name: Name of tool (case-insensitive)

        Returns:
            Tool metadata dict or None if not found
        """
        tool_name_lower = tool_name.lower()

        # Check custom first (higher precedence)
        for name, metadata in self.custom_tools.items():
            if name.lower() == tool_name_lower:
                return dict(metadata)

        # Then check core
        for name, metadata in self.core_tools.items():
            if name.lower() == tool_name_lower:
                return dict(metadata)

        return None

    def create_install_plan_for_categories(self, categories: List[str]) -> InstallPlan:
        """Create install plan for specific categories."""
        missing = self.get_missing()
        filtered = [t for t in missing if t["category"] in categories]
        return self._create_install_plan(filtered)

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
            else:
                logger.warning(f"Tool not found in metadata: {name}")

        return self._create_install_plan(filtered)

    def _create_install_plan(self, tools: List[Dict]) -> InstallPlan:
        """Create install plan from tool list. Never mutates input."""
        # Create runtime copies for dependency info
        runtime_tools = []
        categories = set()

        for tool in tools:
            runtime_tool = dict(tool)
            deps = self._check_dependencies(runtime_tool)

            # Store dependency info in runtime copy only
            runtime_tool["dependencies_ok"] = deps.available
            runtime_tool["dependency_hint"] = deps.hint if not deps.available else ""
            runtime_tool["installer_hint"] = deps.installer_hint

            runtime_tools.append(runtime_tool)
            categories.add(tool.get("category", "unknown"))

        # Group by ecosystem
        grouped = self._group_by_ecosystem(runtime_tools)

        return InstallPlan(
            tools=grouped,
            total=len(runtime_tools),
            categories=list(categories)
        )

    def _group_by_ecosystem(self, tools: List[Dict]) -> Dict[str, List[Dict]]:
        """Group tools by ecosystem."""
        grouped = {}
        for tool in tools:
            ecosystem = tool.get("ecosystem", "unknown")
            if ecosystem not in grouped:
                grouped[ecosystem] = []
            grouped[ecosystem].append(tool)
        return grouped

    def update_tool(self, tool_name: str, dry_run: bool = False) -> Result:
        """Update a single tool to latest version.

        Args:
            tool_name: Name of tool to update
            dry_run: If True, only show what would be done

        Returns:
            Result indicating success/failure
        """
        metadata = self._get_tool_metadata(tool_name)
        if not metadata:
            return Result(
                success=False,
                code=ErrorCode.NOT_FOUND,
                message=f"Tool {tool_name} not found",
                stage="update"
            )

        with self._install_lock:
            result = update_tool(metadata, dry_run=dry_run)
            if result.success and not dry_run:
                self._clear_cache()
                logger.info(f"Tool {tool_name} updated successfully")
            return result

    def update_all(self, dry_run: bool = False) -> Dict[str, Result]:
        """Update all installed tools.

        Args:
            dry_run: If True, only show what would be done

        Returns:
            Dict mapping tool names to update results
        """
        detected = self.detect(use_cache=False)  # Force fresh detection
        installed = [t for t in detected if t.status == ToolStatus.INSTALLED]

        results = {}
        for tool in installed:
            results[tool.name] = self.update_tool(tool.name, dry_run=dry_run)

        if not dry_run:
            self._clear_cache()
            logger.info(f"Updated {len(installed)} tools")

        return results

    def present_install_plan(self, plan: InstallPlan, dry_run: bool = False):
        """Show plan and get user approval.

        Args:
            plan: Install plan to present
            dry_run: If True, only show what would be done
        """
        print("\n" + "="*60)
        print(f"INSTALLATION PLAN: {plan.total} tools")
        print("="*60)

        for ecosystem, tools in plan.tools.items():
            print(f"\n{ecosystem.upper()} ({len(tools)} tools):")
            for tool in tools:
                status = "✓" if tool.get("dependencies_ok", True) else "✗"
                deps_hint = tool.get("dependency_hint", "")
                print(f"  [{status}] {tool['name']} - {tool.get('category', 'unknown')}")
                if deps_hint:
                    print(f"      ⚠️  {deps_hint}")

        if dry_run:
            print("\n" + "="*60)
            print("DRY RUN MODE - No actual installations will occur")
            print("="*60)
            return

        print("\n" + "="*60)
        choice = input("Install all? [y/n/s] (s=select): ").lower()

        if choice == "s":
            selected = self._interactive_select(plan.tools)
        elif choice == "y":
            selected = [t for tools in plan.tools.values() for t in tools]
        else:
            print("Installation cancelled")
            return

        self._execute_install(selected)

    def _interactive_select(self, grouped: Dict[str, List[Dict]]) -> List[Dict]:
        """Interactive tool selection."""
        selected = []

        for ecosystem, tools in grouped.items():
            print(f"\n{ecosystem.upper()}:")
            for i, tool in enumerate(tools):
                deps_ok = "✓" if tool.get("dependencies_ok", True) else "✗"
                print(f"  [{i}] {deps_ok} {tool['name']} - {tool.get('category', 'unknown')}")

            choice = input(f"Select tools (comma-separated numbers, or 'all'): ").lower()

            if choice == "all":
                selected.extend(tools)
            else:
                try:
                    indices = [int(x.strip()) for x in choice.split(',')]
                    for i in indices:
                        if 0 <= i < len(tools):
                            selected.append(tools[i])
                except ValueError:
                    print("Invalid selection, skipping this ecosystem")

        return selected

    def _execute_install(self, tools: List[Dict], dry_run: bool = False):
        """Install with approval guard and concurrency control.

        Args:
            tools: List of tools to install
            dry_run: If True, only show what would be done
        """
        with self._install_lock:
            results = {"installed": [], "failed": [], "skipped": []}
            total = len(tools)

            for idx, tool in enumerate(tools):
                print(f"\n[{idx+1}/{total}] Processing {tool['name']}...")

                # Safety check for high-risk tools
                if self._is_high_risk(tool):
                    print(f"⚠️  High-risk usage tool: {tool['name']}")
                    print("   This tool can be used for offensive security testing.")
                    if not self._get_approval([tool]):
                        print(f"Skipped {tool['name']} (user declined)")
                        results["skipped"].append(tool["name"])
                        continue

                # Check dependencies
                deps = self._check_dependencies(tool)
                if not deps.available:
                    print(f"Skipped {tool['name']}: {deps.hint}")
                    results["skipped"].append({"tool": tool["name"], "reason": deps.hint})
                    continue

                # Install
                result = install_tool(tool, dry_run=dry_run)

                if result.success:
                    print(f"✓ {tool['name']} installed")
                    results["installed"].append(tool["name"])

                    # Show PATH hints
                    if result.hint:
                        print(f"  Hint: {result.hint}")
                else:
                    print(f"✗ {tool['name']} failed: {result.message}")
                    if result.hint:
                        print(f"  Hint: {result.hint}")

                    results["failed"].append({
                        "tool": tool["name"],
                        "error": result.message,
                        "hint": result.hint
                    })

                    # Record failed install
                    self._record_failed_install(tool["name"], result)

                    # Stop on critical errors
                    if result.code in CriticalErrorSet.CRITICAL:
                        print(f"\n⚠️  Critical error: {result.message}")
                        print("Stopping batch installation")
                        break

            # Clear cache after installation
            if not dry_run:
                self._clear_cache()

            # Summary
            print("\n" + "="*60)
            print("INSTALLATION SUMMARY")
            print("="*60)
            print(f"✓ Installed: {len(results['installed'])}")
            print(f"✗ Failed: {len(results['failed'])}")
            print(f"⊘ Skipped: {len(results['skipped'])}")

            if results['failed']:
                print("\nFailed tools:")
                for item in results['failed']:
                    print(f"  - {item['tool']}: {item['error']}")

            if not dry_run:
                # Re-detect to show final state
                print("\nRe-detecting tools...")
                self.detect(use_cache=False)

    def _is_high_risk(self, tool: Dict) -> bool:
        """Check if tool requires explicit approval."""
        return tool.get("name", "").lower() in self.HIGH_RISK_TOOLS

    def _get_approval(self, tools: List[Dict]) -> bool:
        """Get user approval for installation."""
        tool_names = ', '.join(t['name'] for t in tools)
        choice = input(f"Approve installation of {tool_names}? [y/n]: ").lower()
        return choice == 'y'

    def _check_dependencies(self, tool: Dict) -> DependencyCheck:
        """Check if required dependencies are available."""
        ecosystem = tool["ecosystem"]
        missing = []
        installer_hint = ""

        if ecosystem == "go" and not shutil.which("go"):
            missing.append("go (required for Go tools)")
        elif ecosystem == "cargo" and not shutil.which("cargo"):
            missing.append("cargo (required for Rust tools)")
        elif ecosystem == "pip":
            # Prefer pipx for isolation
            if shutil.which("pipx"):
                installer_hint = "pipx"
            elif not shutil.which("pip3"):
                missing.append("pip3 (required for Python tools)")

        if missing:
            return DependencyCheck(
                available=False,
                missing=missing,
                hint=f"Install dependencies first: {' '.join(missing)}",
                installer_hint=installer_hint
            )

        return DependencyCheck(available=True, installer_hint=installer_hint)

    def _load_cache(self) -> Optional[List[ToolInfo]]:
        """Load cached detection results if not expired. Thread-safe."""
        if not os.path.exists(self._cache_path):
            return None

        try:
            with self._cache_lock:  # Use cache lock, not install lock
                with open(self._cache_path, 'r') as f:
                    data = json.load(f)

            cached_time = data.get('timestamp', 0)
            if time.time() - cached_time > self._cache_ttl:
                return None

            tools = []
            for item in data.get('tools', []):
                try:
                    # Convert status string back to enum
                    item['status'] = ToolStatus(item['status'])
                    tools.append(ToolInfo(**item))
                except Exception as e:
                    logger.warning(f"Failed to load cached tool info: {e}")
                    continue

            return tools
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return None

    def _save_cache(self, tools: List[ToolInfo]):
        """Save detection results to cache. Thread-safe."""
        try:
            with self._cache_lock:  # Use cache lock, not install lock
                with open(self._cache_path, 'w') as f:
                    json.dump({
                        'timestamp': time.time(),
                        'tools': [asdict(t) for t in tools]
                    }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _clear_cache(self):
        """Clear cached detection results."""
        try:
            with self._cache_lock:
                if os.path.exists(self._cache_path):
                    os.remove(self._cache_path)
                    logger.info("Cache cleared")
        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")

    def _record_failed_install(self, tool_name: str, error: Result):
        """Record failed installation for future reference."""
        try:
            with open(self._failed_installs_path, 'r') as f:
                failed = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            failed = {}

        failed[tool_name] = {
            'error': error.code.value if error.code else None,
            'message': error.message,
            'last_attempt': time.time(),
            'retry_count': failed.get(tool_name, {}).get('retry_count', 0) + 1
        }

        try:
            with open(self._failed_installs_path, 'w') as f:
                json.dump(failed, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to record failed install: {e}")

    def _get_failed_installs(self) -> Dict[str, Dict]:
        """Get history of failed installations."""
        try:
            if os.path.exists(self._failed_installs_path):
                with open(self._failed_installs_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def list_available(self, category: str = None) -> List[Dict[str, Any]]:
        """List all available tools.

        Args:
            category: Optional category filter

        Returns:
            List of tool dicts
        """
        detected = self.detect()

        if category:
            detected = [t for t in detected if t.category == category]

        return [t.to_dict() for t in detected]
```

### Data Flow

```
User Request → manager.py
    → load metadata (metadata.py, custom_tools.yaml)
    → resolve tool names (resolver.py)
    → call detector (detector.py)
    → filter/group results
    → check dependencies
    → present install plan
    → get user approval
    → call installer (installer.py)
    → track progress
    → re-detect
    → report results
```

---

## Installation Workflow

### Complete Workflow

```
detect
  → resolve aliases/replacements
  → remove deprecated/bad entries
  → group by ecosystem
  → check dependencies
  → show selectable install plan
  → always ask approval
  → extra approval for high-risk offensive tools
  → install sequentially
  → re-detect
  → report installed / failed / skipped / manual
```

### Example Flow

```
User: "install missing tools"
  ↓
manager.install_batch()
  ↓
1. Detect all tools
2. Resolve: subjack → subzy, remove wifitex (deprecated)
3. Filter missing (not in PATH)
4. Group by ecosystem:
     APT: nmap, masscan, aircrack-ng, zaproxy, ncat
     GO: nuclei, subfinder, httpx, dnsx, subzy
     PIP/PIPX: dirsearch, volatility3
     CARGO: rustscan
     MANUAL: metasploit, burpsuite
5. Check dependencies:
     ✓ go (required for Go tools)
     ✓ cargo (required for Rust tools)
     ✓ pipx (will use for Python tools)
6. Show selectable install plan
7. User selects tools
8. SAFETY CHECK:
     - If tool is high-risk (metasploit, sqlmap, hydra) → FORCE explicit approval
     - Show: "⚠️ High-risk offensive tool. Installation requires explicit approval."
9. Ask: "Proceed with installation? [y/n]"
10. Install sequentially:
     - APT tools with sudo
     - GO/CARGO tools without sudo
     - PIPX tools without sudo (isolated)
     - MANUAL tools → show install instructions
11. Re-detect → report results
```

### Ecosystem Grouping (Corrected)

```
APT: nmap, masscan, aircrack-ng, zaproxy, ncat
GO: nuclei, subfinder, httpx, dnsx, subzy
PIP/PIPX: dirsearch, volatility3
CARGO: rustscan
MANUAL: metasploit, burpsuite
```

### Dependency Checking

```python
def _check_dependencies(self, tool: Dict) -> DependencyCheck:
    ecosystem = tool["ecosystem"]
    missing = []

    if ecosystem == "go" and not shutil.which("go"):
        missing.append("go (required for Go tools)")

    if ecosystem == "cargo" and not shutil.which("cargo"):
        missing.append("cargo (required for Rust tools)")

    if ecosystem == "pip":
        # Prefer pipx for isolation
        if shutil.which("pipx"):
            tool["installer_hint"] = "pipx"
        elif not shutil.which("pip3"):
            missing.append("pip3 (required for Python tools)")

    if missing:
        return DependencyCheck(
            available=False,
            missing=missing,
            hint=f"Install dependencies first: {' '.join(missing)}"
        )

    return DependencyCheck(available=True)
```

### Safety Rules

**High-risk tools require explicit approval:**
```python
HIGH_RISK_TOOLS = {"metasploit", "sqlmap", "hydra", "exploitdb"}

def _is_high_risk(self, tool: Dict) -> bool:
    return tool["name"].lower() in HIGH_RISK_TOOLS
```

**Never auto-install dangerous/offensive tools in any mode. All installs require explicit user approval.**

---

## Error Handling

### Structured Error Codes

```python
class ErrorCode:
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    INSTALL_FAILED = "install_failed"
    DEPENDENCY_MISSING = "dependency_missing"
    NETWORK_ERROR = "network_error"
    NOT_IN_PATH = "not_in_path"
    BROKEN = "broken"

class ToolStatus:
    INSTALLED = "installed"
    NOT_FOUND = "not_found"
    NOT_IN_PATH = "not_in_path"
    PERMISSION_DENIED = "permission_denied"
    BROKEN = "broken"
    OUTDATED = "outdated"

CRITICAL_ERRORS = {
    ErrorCode.PERMISSION_DENIED,
    ErrorCode.DEPENDENCY_MISSING,
}

RETRYABLE_ERRORS = {
    ErrorCode.TIMEOUT,
    ErrorCode.NETWORK_ERROR,
}
```

### Result Objects

```python
@dataclass
class Result:
    success: bool
    code: Optional[str] = None
    message: str = ""
    stderr: str = ""
    hint: str = ""

@dataclass
class ToolInfo:
    name: str
    status: str
    version: str = "unknown"
    path: str = ""
    error: str = ""
    hint: str = ""

@dataclass
class DependencyCheck:
    available: bool
    missing: List[str] = field(default_factory=list)
    hint: str = ""
    installer_hint: str = ""
```

### Detection Error Handling

```python
def detect_tool(metadata: Dict) -> ToolInfo:
    try:
        path = shutil.which(metadata["name"])
        if not path:
            return ToolInfo(
                name=metadata["name"],
                status=ToolStatus.NOT_FOUND
            )

        version = get_tool_version(metadata["version_flags"])
        return ToolInfo(
            name=metadata["name"],
            status=ToolStatus.INSTALLED,
            version=version,
            path=path
        )

    except PermissionError:
        return ToolInfo(
            name=metadata["name"],
            status=ToolStatus.PERMISSION_DENIED,
            error="Permission denied",
            hint="Check file permissions"
        )

    except subprocess.TimeoutExpired:
        return ToolInfo(
            name=metadata["name"],
            status=ToolStatus.INSTALLED,
            version="timeout",
            warning="Tool unresponsive"
        )
```

### Installation Error Handling

```python
def install_apt(tool: Dict, sudo: bool) -> Result:
    cmd = f"{'sudo ' if sudo else ''}apt install -y {tool['name']}"

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

        if result.returncode != 0:
            return Result(
                success=False,
                code=ErrorCode.INSTALL_FAILED,
                message="Install failed",
                stderr=result.stderr.decode(),
                hint="Check apt repository or run 'apt update'"
            )

        return Result(success=True)

    except subprocess.TimeoutExpired:
        return Result(
            success=False,
            code=ErrorCode.TIMEOUT,
            message="Installation timeout",
            hint="Network issue or large package"
        )

    except PermissionError:
        return Result(
            success=False,
            code=ErrorCode.PERMISSION_DENIED,
            message="Permission denied",
            hint="Use sudo or run as root"
        )
```

### Retry Strategy

```python
def install_with_retry(tool: Dict, max_attempts: int = 2) -> Result:
    for attempt in range(max_attempts):
        result = installer.install_tool(tool)

        if result.success:
            return result

        if result.code not in RETRYABLE_ERRORS:
            break  # Don't retry non-retryable errors

    return result
```

### Batch Error Handling

```python
def install_batch(self, tools: List[Dict]):
    results = {
        "installed": [],
        "failed": [],
        "skipped": []
    }

    for tool in tools:
        try:
            # Check dependencies
            deps = self._check_dependencies(tool)
            if not deps.available:
                results["skipped"].append({
                    "tool": tool["name"],
                    "reason": deps.hint
                })
                continue

            # Install
            result = install_with_retry(tool)

            if result.success:
                results["installed"].append(tool["name"])
            else:
                results["failed"].append({
                    "tool": tool["name"],
                    "code": result.code,
                    "error": result.message,
                    "hint": result.hint
                })

                # Stop on critical errors
                if result.code in CRITICAL_ERRORS:
                    self._report_critical_failure(result)
                    return results

        except Exception as e:
            results["failed"].append({
                "tool": tool["name"],
                "error": f"Unexpected error: {str(e)}",
                "hint": "Check logs for details"
            })

    return results
```

### Error Hierarchy

1. **Critical** → Stop batch, report immediately (permission, missing dependencies)
2. **Warning** → Continue, log, show in summary (timeout, network error)
3. **Info** → Note, don't affect outcome (tool not in PATH)

---

## Testing Strategy

### Unit Tests

**test_detector.py**
- Test `detect_tool()` with mock metadata
- Test `get_tool_version()` with multiple version flags
- Test detection of installed vs missing tools
- Test permission denied handling
- Test timeout handling

**test_resolver.py**
- Test alias resolution
- Test deprecation handling
- Test replacement mapping
- Test bad version command overrides

**test_installer.py**
- Test apt installer with dry-run
- Test go installer
- Test pip/pipx preference
- Test cargo installer
- Test binary installer
- Test error code handling

**test_manager.py**
- Test workflow orchestration
- Test metadata loading
- Test filtering by category
- Test install plan creation
- Test approval guard

### Integration Tests

**test_tool_management.py**
- End-to-end: detect → install → verify
- Test batch installation
- Test custom tools YAML loading
- Test dependency checking flow

**test_yaml_loading.py**
- Load custom_tools.yaml
- Validate schema
- Test malformed YAML handling

### Test Doubles

```python
# Mock detection
def mock_which(tool):
    return f"/usr/bin/{tool}" if tool == "nmap" else None

# Mock installation
def mock_subprocess_run(cmd, **kwargs):
    return Mock(returncode=0, stdout=b"7.94")

# Fake YAML files
@pytest.fixture
def fake_yaml(tmp_path):
    yaml_file = tmp_path / "custom_tools.yaml"
    yaml_file.write_text("tools:\n  test:\n    name: test\n    ecosystem: apt\n    install_cmd: apt install test\n    version_flags:\n      - --version\n")
    return yaml_file
```

### Coverage Targets

- **Detector:** 95%+ (pure functions, easy to test)
- **Resolver:** 90%+ (data transformations)
- **Installer:** 80%+ (external deps, integration-heavy)
- **Manager:** 85%+ (orchestration logic)

---

## AI Integration

### ToolManager as AI Interface

```python
manager = ToolManager()

# "What tools do I have?"
available = manager.list_available()

# "What's missing for recon?"
missing = manager.get_missing(category="recon")

# "Suggest tools for port scanning"
suggested = manager.suggest_tools_for_capability("port_scan")
```

### Capability Mapping

```python
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
        "volatility": {"priority": 8, "speed": "medium", "accuracy": "high"},
        "volatility3": {"priority": 10, "speed": "medium", "accuracy": "high"}
    },
}

class ToolSelector:
    """AI decision layer for tool selection based on requirements."""

    def __init__(self, manager: ToolManager):
        self.manager = manager
        self.capability_map = CAPABILITY_MAP

    def select_best_tool(self, capability: str, preference: str = "balanced") -> Optional[str]:
        """
        Select best tool for a capability based on preference.

        Args:
            capability: Capability name (e.g., "port_scan")
            preference: Selection preference: 'speed', 'accuracy', 'balanced'

        Returns:
            Best tool name or None if no tools available
        """
        if capability not in self.capability_map:
            logger.warning(f"Unknown capability: {capability}")
            return None

        tools = self.capability_map[capability]
        available = [t for t in tools.keys() if self.manager.is_available(t)]

        if not available:
            logger.info(f"No available tools for capability: {capability}")
            return None

        if preference == "speed":
            # Sort by speed (fast > medium > slow)
            speed_order = {"fast": 3, "medium": 2, "slow": 1}
            return max(available, key=lambda t: speed_order[tools[t]["speed"]])

        elif preference == "accuracy":
            # Sort by accuracy (very_high > high > medium)
            accuracy_order = {"very_high": 3, "high": 2, "medium": 1}
            return max(available, key=lambda t: accuracy_order[tools[t]["accuracy"]])

        else:  # balanced
            # Sort by priority
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
```

### AI Integration Rules

```python
# AI uses ToolSelector for intelligent tool selection
selector = ToolSelector(manager)

# AI can suggest best tool for capability
def suggest_best_tool(capability: str, preference: str = "balanced") -> Optional[str]:
    return selector.select_best_tool(capability, preference)

# AI can get all available tools for capability
def get_available_tools(capability: str) -> List[str]:
    return selector.get_tools_by_capability(capability)

# AI can create install plans for capabilities
def create_install_plan_for_capability(capability: str) -> InstallPlan:
    missing = selector.get_missing_tools_for_capability(capability)
    return manager.create_install_plan_for_tools(missing)

# AI CANNOT silently install tools
def install_tools_for_capability(capability: str):
    plan = create_install_plan_for_capability(capability)
    manager.present_install_plan(plan)  # User must approve
    # No direct install calls from AI
```

### Safety Layer

```python
def is_safe_to_run(self, tool_name: str) -> bool:
    """Check if tool is safe for AI to suggest/execute."""
    metadata = self.get_tool_metadata(tool_name)

    # High-risk tools require explicit approval
    if self._is_high_risk(tool_name):
        return False

    # Check if tool has valid scope
    if not self._has_valid_scope(tool_name):
        return False

    return True
```

### AI Integration Constraints

1. **AI can suggest tools** - Based on capability mapping
2. **AI can create install plans** - For user review
3. **AI cannot silently install tools** - All installs require manager approval flow
4. **High-risk tools always require approval** - Even in suggestions
5. **AI must check tool availability** - Before suggesting or running

### Planner Integration

```python
# Planner uses this interface
class ToolCapabilityLayer:
    def __init__(self):
        self.manager = ToolManager()

    def get_available_tools(self, capability: str) -> List[str]:
        """Get installed tools for a capability."""
        all_tools = CAPABILITY_MAP.get(capability, [])
        return [t for t in all_tools if self.manager.is_available(t)]

    def get_missing_tools(self, capability: str) -> List[str]:
        """Get missing tools for a capability."""
        all_tools = CAPABILITY_MAP.get(capability, [])
        return [t for t in all_tools if not self.manager.is_available(t)]

    def plan_tool_installation(self, capability: str) -> InstallPlan:
        """Create install plan for capability."""
        missing = self.get_missing_tools(capability)
        return self.manager.create_install_plan(missing)
```

---

## File Changes

### New Files

1. **assistant/tools/models.py** - Shared dataclasses: Result, ToolInfo, DependencyCheck, InstallPlan, ErrorCode, ToolStatus
2. **assistant/tools/metadata.py** - CORE_TOOLS catalog (80-100 tools)
3. **assistant/tools/resolver.py** - Aliases, replacements, deprecated tools
4. **assistant/tools/manager.py** - ToolManager class
5. **assistant/tools/installer.py** - Ecosystem installers
6. **assistant/tools/custom_tools.yaml** - User additions (empty initially)

### Modified Files

1. **assistant/tools/detector.py**
   - Remove COMMON_TOOLS (move to metadata.py)
   - Make `detect_tool()` pure function
   - Add `get_tool_version()` with multiple flag support
   - Ensure NO install calls
   - Add structured error handling

2. **assistant/tools/runner.py**
   - Keep as-is (backward compatible)
   - Update imports if needed

### Unchanged Files

- All tool wrappers (nmap_tool.py, nuclei_tool.py, etc.)
- All other assistant modules

---

## Implementation Steps

1. **Create models.py** - Define all shared dataclasses and enums
2. **Create metadata.py** - Move and expand COMMON_TOOLS with full metadata
3. **Create resolver.py** - Implement aliases, replacements, deprecation handling
4. **Refactor detector.py** - Make pure, remove data, add structured errors
5. **Create installer.py** - Implement ecosystem installers with PATH warnings
6. **Create manager.py** - Implement ToolManager class with locks, cache, validation
7. **Create custom_tools.yaml** - Empty template with schema
8. **Create selector.py** - Implement ToolSelector for AI decision layer
9. **Update imports** - Update runner.py if needed
10. **Write tests** - Unit tests for all components
11. **Integration test** - End-to-end workflow test
12. **Documentation** - Update CUSTOM_TOOLS.md, ADDING_TOOLS.md

---

## Success Criteria

1. ✅ Shared models defined in models.py (Result, ToolInfo, DependencyCheck, InstallPlan, ErrorCode, ToolStatus)
2. ✅ Detector is pure (no install calls, no data ownership, no metadata mutation)
3. ✅ All 59+ core tools have correct metadata (version_required, binary, ecosystem)
4. ✅ Version detection works for all tools (correct flags, binary detection)
5. ✅ Installation works for all ecosystems (apt, go, pip, cargo, binary)
6. ✅ Update mechanism works (update_tool, update_all)
7. ✅ Dependency checking prevents failed installs
8. ✅ Safety guards prevent unauthorized high-risk tool installation
9. ✅ Batch approval flow works correctly
10. ✅ Error handling provides actionable feedback (structured codes)
11. ✅ Version constraint checking (OUTDATED status) with proper comparison
12. ✅ Tool location awareness (path stored in ToolInfo)
13. ✅ Install lock prevents concurrent installations
14. ✅ Cache layer with TTL (5 minutes) and separate cache lock
15. ✅ Failure memory for learning from errors
16. ✅ AI can suggest tools and create plans but not silently install
17. ✅ ToolSelector for intelligent tool selection (speed/accuracy/balanced)
18. ✅ Custom tools can be added via YAML with validation
19. ✅ Custom tools override core tools (proper precedence)
20. ✅ Tool names normalized to lowercase
21. ✅ PATH warnings shown for Go/Cargo/Pip tools
22. ✅ Dry-run mode implemented
23. ✅ Progress callback mechanism
24. ✅ Logging throughout system
25. ✅ Metadata validation on load
26. ✅ Cache cleared after installs/updates
27. ✅ Tests achieve coverage targets
28. ✅ Backward compatible with existing tool wrappers

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Wrong install commands | Tools fail to install | Test each ecosystem installer in CI |
| Version detection fails | Tools marked missing | Multiple version flags, fallback to `which` |
| Dependency missing | Install fails | Pre-check dependencies, show clear hints |
| User approves wrong tools | Security risk | High-risk tools require extra approval |
| YAML schema invalid | Custom tools fail | Validate schema on load, show errors |
| Path issues after install | Tool not found | Re-detect after install, show PATH hints |
| Sudo not available | APT installs fail | Check sudo availability, show alternative |

---

## Future Enhancements

1. **Auto-discovery** - Scan PATH for unknown tools, suggest additions to custom_tools.yaml
2. **Tool health checks** - Verify tools actually work (not just installed)
3. **Tool profiles** - Pre-defined tool sets for bug bounty, pentesting, forensics
4. **Installation presets** - Quick install of tool categories
5. **Uninstall capability** - Clean tool removal
6. **Tool verification** - Hash verification for downloaded binaries
7. **Advanced failure recovery** - Automatic retry strategies for known failures

---

## Sign-Off

Design complete and approved.

**Next Steps:**
1. Write implementation plan using writing-plans skill
2. Begin implementation following plan
3. Test at each milestone
4. Update documentation
