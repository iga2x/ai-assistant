# Tool Management System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an intelligent tool management system for AI assistant with detection, installation, update, and lifecycle management of security tools.

**Architecture:** Four-layer architecture with separation of concerns: Data Layer (metadata, YAML), Detection Layer (pure functions), Management Layer (orchestrator), Installation Layer (ecosystem installers).

**Tech Stack:** Python 3.8+, Pydantic, packaging (version comparison), PyYAML, threading, subprocess

---

## File Structure

**New Files:**
- `assistant/tools/models.py` - Shared dataclasses and enums (Result, ToolInfo, DependencyCheck, InstallPlan, ErrorCode, ToolStatus)
- `assistant/tools/metadata.py` - CORE_TOOLS catalog (80-100 curated security tools with full metadata)
- `assistant/tools/resolver.py` - Aliases, replacements, deprecated tools, bad version commands
- `assistant/tools/manager.py` - ToolManager class (orchestrator)
- `assistant/tools/installer.py` - Ecosystem installers (apt, go, pip, cargo, binary)
- `assistant/tools/custom_tools.yaml` - User additions template
- `assistant/tools/selector.py` - ToolSelector for AI decision layer
- `tests/tools/test_models.py` - Test shared dataclasses
- `tests/tools/test_detector.py` - Test pure detection functions
- `tests/tools/test_installer.py` - Test ecosystem installers
- `tests/tools/test_manager.py` - Test ToolManager orchestration
- `tests/tools/test_resolver.py` - Test alias/replacement resolution
- `tests/tools/test_selector.py` - Test AI tool selection
- `tests/tools/integration/test_tool_management.py` - End-to-end workflow tests

**Modified Files:**
- `assistant/tools/detector.py` - Refactor to pure detection, remove COMMON_TOOLS, add structured errors
- `assistant/tools/runner.py` - Update imports if needed (backward compatible)
- `pyproject.toml` - Add dependencies (packaging, pyyaml)

**Unchanged Files:**
- All existing tool wrappers (nmap_tool.py, nuclei_tool.py, etc.)

---

## Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add required dependencies to pyproject.toml**

```toml
[tool.poetry.dependencies]
python = "^3.8"
pydantic = "^2.0"
packaging = "^21.0"
pyyaml = "^6.0"

[tool.poetry.dev-dependencies]
pytest = "^7.0"
pytest-cov = "^4.0"
```

- [ ] **Step 2: Install dependencies**

Run: `poetry install`
Expected: All packages installed successfully

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add tool manager dependencies (packaging, pyyaml)"
```

---

## Task 2: Create Shared Models

**Files:**
- Create: `assistant/tools/models.py`
- Create: `tests/tools/test_models.py`

- [ ] **Step 1: Create models.py with dataclasses and enums**

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

- [ ] **Step 2: Create test_models.py**

```python
"""Test shared data models."""

import pytest
from assistant.tools.models import (
    ErrorCode, ToolStatus, Result, ToolInfo, DependencyCheck, InstallPlan,
    CriticalErrorSet, RetryableErrorSet
)


def test_error_codes():
    """Test ErrorCode enum values."""
    assert ErrorCode.PERMISSION_DENIED.value == "permission_denied"
    assert ErrorCode.TIMEOUT.value == "timeout"
    assert ErrorCode.NOT_FOUND.value == "not_found"


def test_tool_status_enum():
    """Test ToolStatus enum values."""
    assert ToolStatus.INSTALLED.value == "installed"
    assert ToolStatus.NOT_FOUND.value == "not_found"
    assert ToolStatus.OUTDATED.value == "outdated"


def test_result_dataclass():
    """Test Result dataclass."""
    result = Result(
        success=True,
        code=ErrorCode.NOT_FOUND,
        message="Tool not found",
        stage="detect"
    )

    assert result.success is True
    assert result.code == ErrorCode.NOT_FOUND
    assert result.message == "Tool not found"
    assert result.stage == "detect"


def test_result_to_dict():
    """Test Result serialization."""
    result = Result(
        success=False,
        code=ErrorCode.PERMISSION_DENIED,
        message="Permission denied",
        stage="install"
    )

    result_dict = result.to_dict()

    assert result_dict["success"] is False
    assert result_dict["code"] == "permission_denied"
    assert result_dict["message"] == "Permission denied"
    assert result_dict["stage"] == "install"


def test_tool_info_dataclass():
    """Test ToolInfo dataclass."""
    info = ToolInfo(
        name="nmap",
        status=ToolStatus.INSTALLED,
        version="7.94",
        path="/usr/bin/nmap",
        category="scanner"
    )

    assert info.name == "nmap"
    assert info.status == ToolStatus.INSTALLED
    assert info.version == "7.94"
    assert info.path == "/usr/bin/nmap"
    assert info.category == "scanner"


def test_tool_info_is_available():
    """Test ToolInfo availability check."""
    installed = ToolInfo(name="nmap", status=ToolStatus.INSTALLED)
    outdated = ToolInfo(name="nuclei", status=ToolStatus.OUTDATED)
    missing = ToolInfo(name="masscan", status=ToolStatus.NOT_FOUND)

    assert installed.is_available() is True
    assert outdated.is_available() is True
    assert missing.is_available() is False


def test_dependency_check_dataclass():
    """Test DependencyCheck dataclass."""
    check = DependencyCheck(
        available=False,
        missing=["go"],
        hint="Go is required"
    )

    assert check.available is False
    assert check.missing == ["go"]
    assert check.hint == "Go is required"


def test_install_plan_dataclass():
    """Test InstallPlan dataclass."""
    plan = InstallPlan(
        tools={
            "apt": [{"name": "nmap"}],
            "go": [{"name": "nuclei"}]
        },
        total=2,
        categories=["scanner", "recon"]
    )

    assert plan.total == 2
    assert "apt" in plan.tools
    assert "go" in plan.tools
    assert plan.categories == ["scanner", "recon"]


def test_critical_error_set():
    """Test CriticalErrorSet contains correct errors."""
    assert ErrorCode.PERMISSION_DENIED in CriticalErrorSet.CRITICAL
    assert ErrorCode.DEPENDENCY_MISSING in CriticalErrorSet.CRITICAL
    assert ErrorCode.NOT_FOUND in CriticalErrorSet.CRITICAL
    assert ErrorCode.TIMEOUT not in CriticalErrorSet.CRITICAL


def test_retryable_error_set():
    """Test RetryableErrorSet contains correct errors."""
    assert ErrorCode.TIMEOUT in RetryableErrorSet.RETRYABLE
    assert ErrorCode.NETWORK_ERROR in RetryableErrorSet.RETRYABLE
    assert ErrorCode.PERMISSION_DENIED not in RetryableErrorSet.RETRYABLE
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/tools/test_models.py -v`
Expected: All 11 tests PASS

- [ ] **Step 4: Commit**

```bash
git add assistant/tools/models.py tests/tools/test_models.py
git commit -m "feat: add shared data models for tool management"
```

---

## Task 3: Create Resolver

**Files:**
- Create: `assistant/tools/resolver.py`
- Create: `tests/tools/test_resolver.py`

- [ ] **Step 1: Create resolver.py with alias/replacement logic**

```python
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
```

- [ ] **Step 2: Create test_resolver.py**

```python
"""Test tool name resolution and deprecation handling."""

import pytest
from assistant.tools.resolver import Resolver


def test_resolve_normal_tool():
    """Test resolving normal tool name."""
    resolver = Resolver()
    assert resolver.resolve("nmap") == "nmap"
    assert resolver.resolve("nuclei") == "nuclei"


def test_resolve_alias():
    """Test resolving aliased tool name."""
    resolver = Resolver()
    assert resolver.resolve("netcat") == "nc"
    assert resolver.resolve("ncat") == "nc"


def test_resolve_deprecated_with_replacement():
    """Test resolving deprecated tool with replacement."""
    resolver = Resolver()
    assert resolver.resolve("subjack") == "subzy"


def test_resolve_deprecated_without_replacement():
    """Test resolving deprecated tool without replacement."""
    resolver = Resolver()
    assert resolver.resolve("wifitex") is None


def test_get_version_flags_default():
    """Test getting default version flags."""
    resolver = Resolver()
    flags = resolver.get_version_flags("nmap", ["--version", "-V"])
    assert flags == ["--version", "-V"]


def test_get_version_flags_override():
    """Test getting overridden version flags for problematic tools."""
    resolver = Resolver()
    flags = resolver.get_version_flags("assetfinder", ["--version"])
    assert flags == ["--help"]  # Override from BAD_VERSION_CMDS

    flags = resolver.get_version_flags("john", ["--version"])
    assert flags == ["--list=build-info"]  # Override from BAD_VERSION_CMDS


def test_is_deprecated():
    """Test checking if tool is deprecated."""
    resolver = Resolver()
    assert resolver.is_deprecated("wifitex") is True
    assert resolver.is_deprecated("nmap") is False


def test_get_replacement():
    """Test getting replacement for deprecated tool."""
    resolver = Resolver()
    assert resolver.get_replacement("subjack") == "subzy"
    assert resolver.get_replacement("wifitex") is None
    assert resolver.get_replacement("nmap") is None


def test_case_insensitive_resolution():
    """Test case-insensitive name resolution."""
    resolver = Resolver()
    assert resolver.resolve("NETCAT") == "nc"
    assert resolver.resolve("SubJack") == "subzy"
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/tools/test_resolver.py -v`
Expected: All 9 tests PASS

- [ ] **Step 4: Commit**

```bash
git add assistant/tools/resolver.py tests/tools/test_resolver.py
git commit -m "feat: add tool name resolver with alias/deprecation handling"
```

---

## Task 4: Create Metadata Catalog

**Files:**
- Create: `assistant/tools/metadata.py`

- [ ] **Step 1: Create metadata.py with sample CORE_TOOLS**

```python
"""Core tool metadata catalog."""

from typing import Dict, Any
from assistant.tools.models import logger

CORE_TOOLS = {
    "nmap": {
        "name": "nmap",
        "binary": "nmap",
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
    "masscan": {
        "name": "masscan",
        "binary": "masscan",
        "ecosystem": "apt",
        "install_cmd": "apt install masscan",
        "version_flags": ["--version"],
        "version_required": ">=1.0.0",
        "category": "scanner",
        "risk": "high",
        "alternatives": [],
        "docs_url": "https://github.com/robertdavidgraham/masscan",
        "deprecated": False,
        "priority": 8,
        "speed": "fast",
        "accuracy": "medium"
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
    "subfinder": {
        "name": "subfinder",
        "binary": "subfinder",
        "ecosystem": "go",
        "install_cmd": "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
        "version_flags": ["-version"],
        "version_required": ">=2.0.0",
        "category": "recon",
        "risk": "medium",
        "alternatives": [],
        "docs_url": "https://github.com/projectdiscovery/subfinder",
        "deprecated": False,
        "priority": 10,
        "speed": "fast",
        "accuracy": "high"
    },
    "sqlmap": {
        "name": "sqlmap",
        "binary": "sqlmap",
        "ecosystem": "apt",
        "install_cmd": "apt install sqlmap",
        "version_flags": ["--version"],
        "version_required": ">=1.0.0",
        "category": "pentest",
        "risk": "high",
        "alternatives": [],
        "docs_url": "https://sqlmap.org/",
        "deprecated": False,
        "priority": 10,
        "speed": "medium",
        "accuracy": "high"
    },
    "volatility": {
        "name": "volatility",
        "binary": "vol.py",
        "ecosystem": "pip",
        "install_cmd": "pip install volatility",
        "version_flags": ["--version"],
        "version_required": ">=2.0.0",
        "category": "forensics",
        "risk": "low",
        "alternatives": ["volatility3"],
        "docs_url": "https://github.com/volatilityfoundation/volatility",
        "deprecated": False,
        "priority": 8,
        "speed": "medium",
        "accuracy": "high"
    },
    "rustscan": {
        "name": "rustscan",
        "binary": "rustscan",
        "ecosystem": "cargo",
        "install_cmd": "cargo install rustscan",
        "version_flags": ["--version"],
        "version_required": ">=2.0.0",
        "category": "scanner",
        "risk": "high",
        "alternatives": [],
        "docs_url": "https://github.com/RustScan/RustScan",
        "deprecated": False,
        "priority": 7,
        "speed": "fast",
        "accuracy": "medium"
    },
    "httpx": {
        "name": "httpx",
        "binary": "httpx",
        "ecosystem": "go",
        "install_cmd": "go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest",
        "version_flags": ["-version"],
        "version_required": ">=1.0.0",
        "category": "network",
        "risk": "low",
        "alternatives": [],
        "docs_url": "https://github.com/projectdiscovery/httpx",
        "deprecated": False,
        "priority": 9,
        "speed": "fast",
        "accuracy": "high"
    },
    "ffuf": {
        "name": "ffuf",
        "binary": "ffuf",
        "ecosystem": "go",
        "install_cmd": "go install -v github.com/ffuf/ffuf/v2/cmd/ffuf@latest",
        "version_flags": ["-v"],
        "version_required": ">=2.0.0",
        "category": "network",
        "risk": "medium",
        "alternatives": [],
        "docs_url": "https://github.com/ffuf/ffuf",
        "deprecated": False,
        "priority": 10,
        "speed": "fast",
        "accuracy": "high"
    },
    "gobuster": {
        "name": "gobuster",
        "binary": "gobuster",
        "ecosystem": "go",
        "install_cmd": "go install -v github.com/OJ/gobuster/v3/cmd/gobuster@latest",
        "version_flags": ["--version"],
        "version_required": ">=3.0.0",
        "category": "network",
        "risk": "medium",
        "alternatives": [],
        "docs_url": "https://github.com/OJ/gobuster",
        "deprecated": False,
        "priority": 8,
        "speed": "medium",
        "accuracy": "high"
    },
}

# Add more tools as needed - target 80-100 curated security tools
# This is a representative sample showing the structure

logger.info(f"Loaded {len(CORE_TOOLS)} core tools from metadata")
```

- [ ] **Step 2: Verify metadata.py loads without errors**

Run: `python -c "from assistant.tools.metadata import CORE_TOOLS; print(f'Loaded {len(CORE_TOOLS)} tools')"`
Expected: Shows count of loaded tools

- [ ] **Step 3: Commit**

```bash
git add assistant/tools/metadata.py
git commit -m "feat: add core tool metadata catalog"
```

---

## Task 5: Refactor Detector to Pure Functions

**Files:**
- Modify: `assistant/tools/detector.py`
- Create: `tests/tools/test_detector.py`

- [ ] **Step 1: Refactor detector.py to pure detection**

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
    """Pure function. No side effects. No installs. Never mutates metadata.

    Args:
        metadata: Tool metadata dict (name, binary, version_flags, etc.)

    Returns:
        ToolInfo with detection results
    """
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
    """Try multiple version flags in order.

    Args:
        binary: Tool binary name
        version_flags: List of version flags to try (e.g., ["--version", "-V"])

    Returns:
        Version string or "unknown"
    """
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
    """Parse version string from tool output.

    Args:
        stdout: Tool's stdout output
        stderr: Tool's stderr output

    Returns:
        Extracted version string or "unknown"
    """
    # Try stdout first
    version = _extract_version(stdout)
    if version != "unknown":
        return version

    # Fallback to stderr
    version = _extract_version(stderr)
    return version


def _extract_version(text: str) -> str:
    """Extract version number from text using regex.

    Args:
        text: Text to search for version

    Returns:
        Version string or "unknown"
    """
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
    """Check if current version meets requirement (e.g., '>=3.0.0').

    Args:
        current: Current version string
        required: Version requirement (e.g., '>=3.0.0')

    Returns:
        True if version meets requirement
    """
    try:
        if current == "unknown" or not current:
            return False

        spec = SpecifierSet(required)
        return parse_version(current) in spec
    except Exception as e:
        logger.warning(f"Failed to compare versions: current={current}, required={required}, error={e}")
        return False
```

- [ ] **Step 2: Create test_detector.py**

```python
"""Test pure detection functions."""

import pytest
from unittest.mock import patch, Mock
from assistant.tools.detector import (
    detect_tool, get_tool_version, parse_version_output,
    _extract_version, _meets_version_requirement
)
from assistant.tools.models import ToolStatus


def test_detect_tool_installed():
    """Test detecting an installed tool."""
    metadata = {
        "name": "nmap",
        "binary": "python3",
        "version_flags": ["--version"],
        "category": "scanner"
    }

    result = detect_tool(metadata)

    assert result.name == "nmap"
    assert result.status == ToolStatus.INSTALLED
    assert result.version != "unknown"
    assert result.path is not None


def test_detect_tool_not_found():
    """Test detecting a tool that doesn't exist."""
    metadata = {
        "name": "nonexistent_tool_xyz",
        "binary": "nonexistent_tool_xyz",
        "version_flags": ["--version"],
        "category": "scanner"
    }

    result = detect_tool(metadata)

    assert result.name == "nonexistent_tool_xyz"
    assert result.status == ToolStatus.NOT_FOUND
    assert result.path == ""


def test_detect_tool_version_requirement_met():
    """Test version requirement check when met."""
    metadata = {
        "name": "test_tool",
        "binary": "python3",
        "version_flags": ["--version"],
        "version_required": ">=3.0.0",
        "category": "test"
    }

    result = detect_tool(metadata)

    # Python 3 should meet >=3.0.0
    if result.version != "unknown":
        assert result.status == ToolStatus.INSTALLED


def test_detect_tool_version_requirement_not_met():
    """Test version requirement check when not met."""
    metadata = {
        "name": "test_tool",
        "binary": "python3",
        "version_flags": ["--version"],
        "version_required": ">=999.0.0",  # Unrealistic version
        "category": "test"
    }

    result = detect_tool(metadata)

    if result.version != "unknown":
        # Should be marked as outdated
        assert result.status == ToolStatus.OUTDATED
        assert "does not meet requirement" in result.warning


def test_detect_tool_default_binary():
    """Test that binary field defaults to name if not provided."""
    metadata = {
        "name": "python3",
        "version_flags": ["--version"],
        "category": "runtime"
    }

    result = detect_tool(metadata)

    # Should use name as binary
    assert result.status == ToolStatus.INSTALLED


def test_extract_version_simple():
    """Test extracting simple version string."""
    text = "nmap version 7.95"
    version = _extract_version(text)
    assert version == "7.95"


def test_extract_version_with_v_prefix():
    """Test extracting version with v prefix."""
    text = "nuclei v3.2.4"
    version = _extract_version(text)
    assert version == "3.2.4"


def test_extract_version_complex():
    """Test extracting complex version string."""
    text = "Version: 2.5.1-beta"
    version = _extract_version(text)
    assert version == "2.5.1"


def test_extract_version_no_match():
    """Test extracting version when no match found."""
    text = "No version information available"
    version = _extract_version(text)
    assert version == "unknown"


def test_parse_version_output_stdout():
    """Test parsing version from stdout."""
    stdout = "nmap version 7.95"
    stderr = "Some error message"

    version = parse_version_output(stdout, stderr)
    assert version == "7.95"


def test_parse_version_output_stderr_fallback():
    """Test parsing version from stderr as fallback."""
    stdout = "No version"
    stderr = "nuclei v3.2.4"

    version = parse_version_output(stdout, stderr)
    assert version == "3.2.4"


def test_meets_version_requirement_true():
    """Test version requirement that should be met."""
    assert _meets_version_requirement("3.5.0", ">=3.0.0") is True
    assert _meets_version_requirement("7.95", ">=7.0.0") is True


def test_meets_version_requirement_false():
    """Test version requirement that should not be met."""
    assert _meets_version_requirement("2.0.0", ">=3.0.0") is False
    assert _meets_version_requirement("1.5.0", ">=7.0.0") is False


def test_meets_version_requirement_unknown():
    """Test version requirement with unknown current version."""
    assert _meets_version_requirement("unknown", ">=3.0.0") is False
    assert _meets_version_requirement("", ">=3.0.0") is False


def test_get_tool_version_timeout():
    """Test version detection with timeout."""
    # This test may take 2 seconds due to timeout
    version = get_tool_version("sleep", ["5"])  # Will timeout
    assert version == "unknown"


def test_detect_tool_permission_denied():
    """Test detection when permission is denied."""
    metadata = {
        "name": "test_tool",
        "binary": "sudo",  # May not have permissions
        "version_flags": ["--version"],
        "category": "test"
    }

    result = detect_tool(metadata)

    # Either works or returns permission denied
    if result.status == ToolStatus.PERMISSION_DENIED:
        assert "Permission denied" in result.error
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/tools/test_detector.py -v`
Expected: All 14+ tests PASS (some may skip depending on environment)

- [ ] **Step 4: Commit**

```bash
git add assistant/tools/detector.py tests/tools/test_detector.py
git commit -m "refactor: convert detector to pure functions with structured errors"
```

---

## Task 6: Create Installer

**Files:**
- Create: `assistant/tools/installer.py`
- Create: `tests/tools/test_installer.py`

- [ ] **Step 1: Create installer.py with ecosystem installers**

```python
"""Ecosystem-specific installers and updaters."""

import os
import shutil
import subprocess
from typing import Dict, Optional

from assistant.tools.models import (
    Result, ErrorCode, CriticalErrorSet, RetryableErrorSet,
    DependencyCheck, logger, ProgressCallback
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
            hint=f"Command: {tool['install_cmd']}",
            stage="install"
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
    """Update one tool to latest version.

    Args:
        tool: Tool metadata dict
        dry_run: If True, only show what would be done
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
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


def install_apt(tool: Dict, sudo: bool, progress_callback=None) -> Result:
    """Install tool via apt package manager.

    Args:
        tool: Tool metadata dict
        sudo: Whether to use sudo
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
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
    """Install Go tool.

    Args:
        tool: Tool metadata dict
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
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
    """Install Python tool. Prefer pipx over system pip.

    Args:
        tool: Tool metadata dict
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
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
    """Install Rust tool via cargo.

    Args:
        tool: Tool metadata dict
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
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
    """Install binary manually.

    Args:
        tool: Tool metadata dict
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating manual installation required
    """
    return Result(
        success=False,
        code=ErrorCode.NOT_FOUND,
        message=f"Binary installation not automated for {tool['name']}",
        hint=f"Manual installation required: {tool['install_cmd']}",
        stage="install"
    )


def show_manual_instructions(tool: Dict) -> Result:
    """Show manual installation instructions.

    Args:
        tool: Tool metadata dict

    Returns:
        Result with manual instructions
    """
    return Result(
        success=False,
        code=ErrorCode.NOT_FOUND,
        message=f"Manual installation required for {tool['name']}",
        hint=f"Install instructions: {tool.get('docs_url', tool['install_cmd'])}",
        stage="install"
    )


def update_apt(tool: Dict, sudo: bool, progress_callback=None) -> Result:
    """Update tool via apt.

    Args:
        tool: Tool metadata dict
        sudo: Whether to use sudo
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
    cmd = f"{'sudo ' if sudo else ''}apt upgrade -y {tool['name']}"

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

        if result.returncode != 0:
            return Result(
                success=False,
                code=ErrorCode.UPDATE_FAILED,
                message="Update failed",
                stderr=result.stderr.decode(),
                hint="Check apt repository or run 'apt update'",
                stage="update"
            )

        return Result(success=True, stage="update")

    except subprocess.TimeoutExpired:
        return Result(
            success=False,
            code=ErrorCode.TIMEOUT,
            message="Update timeout",
            hint="Network issue",
            stage="update"
        )
    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.UPDATE_FAILED,
            message=f"Unexpected error: {str(e)}",
            hint="Check system logs",
            stage="update"
        )


def update_go(tool: Dict, progress_callback=None) -> Result:
    """Update Go tool.

    Args:
        tool: Tool metadata dict
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
    cmd = tool['install_cmd']  # Re-use install command for Go

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=600)

        if result.returncode != 0:
            return Result(
                success=False,
                code=ErrorCode.UPDATE_FAILED,
                message="Go update failed",
                stderr=result.stderr.decode(),
                hint="Check Go installation and network connectivity",
                stage="update"
            )

        return Result(success=True, stage="update")

    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.UPDATE_FAILED,
            message=f"Unexpected error: {str(e)}",
            hint="Check Go installation",
            stage="update"
        )


def update_pip(tool: Dict, progress_callback=None) -> Result:
    """Update Python tool.

    Args:
        tool: Tool metadata dict
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
    if shutil.which("pipx"):
        cmd = f"pipx upgrade {tool['name']}"
    else:
        cmd = f"pip3 install --upgrade --user {tool['name']}"

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

        if result.returncode != 0:
            return Result(
                success=False,
                code=ErrorCode.UPDATE_FAILED,
                message="Pip update failed",
                stderr=result.stderr.decode(),
                hint="Check Python environment",
                stage="update"
            )

        return Result(success=True, stage="update")

    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.UPDATE_FAILED,
            message=f"Unexpected error: {str(e)}",
            hint="Check Python environment",
            stage="update"
        )


def update_cargo(tool: Dict, progress_callback=None) -> Result:
    """Update Rust tool.

    Args:
        tool: Tool metadata dict
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
    cmd = f"cargo install {tool['name']} --force"

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=600)

        if result.returncode != 0:
            return Result(
                success=False,
                code=ErrorCode.UPDATE_FAILED,
                message="Cargo update failed",
                stderr=result.stderr.decode(),
                hint="Check Rust installation",
                stage="update"
            )

        return Result(success=True, stage="update")

    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.UPDATE_FAILED,
            message=f"Unexpected error: {str(e)}",
            hint="Check Rust installation",
            stage="update"
        )


def install_with_retry(tool: Dict, max_attempts: int = 2, progress_callback=None) -> Result:
    """Install with retry for retryable errors.

    Args:
        tool: Tool metadata dict
        max_attempts: Maximum number of retry attempts
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
    for attempt in range(max_attempts):
        result = install_tool(tool, progress_callback=progress_callback)

        if result.success:
            return result

        if result.code not in RetryableErrorSet.RETRYABLE:
            break  # Don't retry non-retryable errors

        logger.info(f"Retryable error, attempt {attempt + 1}/{max_attempts}: {result.message}")

    return result
```

- [ ] **Step 2: Create test_installer.py**

```python
"""Test ecosystem installers."""

import pytest
from unittest.mock import patch, Mock
from assistant.tools.installer import (
    install_tool, install_apt, install_go, install_pip, install_cargo,
    update_tool, install_with_retry, install_binary, show_manual_instructions
)
from assistant.tools.models import ErrorCode


def test_install_tool_dry_run():
    """Test dry run installation."""
    tool = {
        "name": "nmap",
        "ecosystem": "apt",
        "install_cmd": "apt install nmap"
    }

    result = install_tool(tool, dry_run=True)

    assert result.success is True
    assert "Dry run" in result.message
    assert "apt" in result.message


def test_install_tool_unsupported_ecosystem():
    """Test installation with unsupported ecosystem."""
    tool = {
        "name": "test",
        "ecosystem": "unsupported",
        "install_cmd": "echo test"
    }

    result = install_tool(tool, dry_run=False)

    assert result.success is False
    assert result.code == ErrorCode.NOT_FOUND
    assert "Unsupported ecosystem" in result.message


def test_install_binary_returns_manual():
    """Test binary installation returns manual instructions."""
    tool = {
        "name": "custom_tool",
        "ecosystem": "binary",
        "install_cmd": "cp /path/to/tool /usr/local/bin/"
    }

    result = install_binary(tool)

    assert result.success is False
    assert result.code == ErrorCode.NOT_FOUND
    assert "Manual installation required" in result.message


def test_show_manual_instructions():
    """Test manual instruction display."""
    tool = {
        "name": "metasploit",
        "ecosystem": "manual-note",
        "install_cmd": "curl https://...",
        "docs_url": "https://docs.example.com"
    }

    result = show_manual_instructions(tool)

    assert result.success is False
    assert result.code == ErrorCode.NOT_FOUND
    assert "Manual installation required" in result.message


def test_update_tool_dry_run():
    """Test dry run update."""
    tool = {
        "name": "nmap",
        "ecosystem": "apt",
        "install_cmd": "apt install nmap"
    }

    result = update_tool(tool, dry_run=True)

    assert result.success is True
    assert "Dry run" in result.message


def test_update_tool_unsupported_ecosystem():
    """Test update with unsupported ecosystem."""
    tool = {
        "name": "test",
        "ecosystem": "binary",
        "install_cmd": "echo test"
    }

    result = update_tool(tool, dry_run=False)

    assert result.success is False
    assert result.code == ErrorCode.NOT_FOUND
    assert "Update not supported" in result.message


def test_install_with_retry_on_retryable_error():
    """Test retry on retryable errors."""
    tool = {
        "name": "test_tool",
        "ecosystem": "apt",
        "install_cmd": "echo test"
    }

    with patch('assistant.tools.installer.install_tool') as mock_install:
        # First attempt fails with timeout (retryable)
        # Second attempt succeeds
        from assistant.tools.models import Result, ErrorCode

        mock_install.side_effect = [
            Result(success=False, code=ErrorCode.TIMEOUT, message="Timeout"),
            Result(success=True, message="Success")
        ]

        result = install_with_retry(tool, max_attempts=2)

        assert result.success is True
        assert mock_install.call_count == 2


def test_install_with_retry_stops_on_non_retryable():
    """Test retry stops on non-retryable errors."""
    tool = {
        "name": "test_tool",
        "ecosystem": "apt",
        "install_cmd": "echo test"
    }

    with patch('assistant.tools.installer.install_tool') as mock_install:
        # Non-retryable error (permission denied)
        from assistant.tools.models import Result, ErrorCode

        mock_install.return_value = Result(
            success=False,
            code=ErrorCode.PERMISSION_DENIED,
            message="Permission denied"
        )

        result = install_with_retry(tool, max_attempts=2)

        assert result.success is False
        assert mock_install.call_count == 1  # Should not retry
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/tools/test_installer.py -v`
Expected: All 10 tests PASS

- [ ] **Step 4: Commit**

```bash
git add assistant/tools/installer.py tests/tools/test_installer.py
git commit -m "feat: add ecosystem installers (apt, go, pip, cargo, binary)"
```

---

## Task 7: Create Custom Tools YAML Template

**Files:**
- Create: `assistant/tools/custom_tools.yaml`

- [ ] **Step 1: Create custom_tools.yaml template**

```yaml
# Custom tools for AI assistant
# Add your custom tools here following this schema

tools:
  # Example custom tool (remove this example)
  # my-custom-tool:
  #   name: "my-custom-tool"
  #   binary: "my-custom-tool"
  #   ecosystem: "binary"
  #   install_cmd: "cp /path/to/tool /usr/local/bin/"
  #   version_flags:
  #     - "--version"
  #   version_required: ">=1.0.0"
  #   category: "custom"
  #   risk: "low"
  #   alternatives: []
  #   docs_url: ""
  #   deprecated: false
  #   priority: 5
  #   speed: "medium"
  #   accuracy: "medium"

# Schema validation:
# Required fields: name, ecosystem, install_cmd, version_flags
# Optional fields: binary, version_required, category, risk, alternatives, docs_url, deprecated, priority, speed, accuracy
# Valid ecosystems: apt, go, pip, cargo, binary, manual-note
```

- [ ] **Step 2: Commit**

```bash
git add assistant/tools/custom_tools.yaml
git commit -m "feat: add custom tools YAML template"
```

---

## Task 8: Create ToolManager

**Files:**
- Create: `assistant/tools/manager.py`
- Create: `tests/tools/test_manager.py`

- [ ] **Step 1: Create manager.py with ToolManager class**

```python
"""Central API for tool management - orchestrates detection, installation, updates."""

import os
import json
import time
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

        logger.info("ToolManager initialized")

    def _load_core_metadata(self) -> Dict[str, Dict]:
        """Load core tool metadata from metadata.py."""
        from assistant.tools.metadata import CORE_TOOLS
        return CORE_TOOLS

    def _load_custom_tools(self, custom_tools_path: str = None) -> Dict[str, Dict]:
        """Load and validate custom tools from YAML.

        Args:
            custom_tools_path: Path to custom_tools.yaml

        Returns:
            Dictionary of validated custom tools
        """
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
        """Validate tool metadata has required fields.

        Args:
            name: Tool name
            metadata: Tool metadata dict

        Returns:
            True if metadata is valid
        """
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
        """Get tools that are installed but don't meet version requirements.

        Returns:
            List of tool dicts that are outdated
        """
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
        """Create install plan for specific categories.

        Args:
            categories: List of categories to include

        Returns:
            InstallPlan for specified categories
        """
        missing = self.get_missing()
        filtered = [t for t in missing if t["category"] in categories]
        return self._create_install_plan(filtered)

    def create_install_plan_for_tools(self, tool_names: List[str]) -> InstallPlan:
        """Create install plan for specific tools.

        Args:
            tool_names: List of tool names

        Returns:
            InstallPlan for specified tools
        """
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
        """Create install plan from tool list. Never mutates input.

        Args:
            tools: List of tool metadata dicts

        Returns:
            InstallPlan with grouped tools
        """
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
        """Group tools by ecosystem.

        Args:
            tools: List of tool metadata dicts

        Returns:
            Dict mapping ecosystem to list of tools
        """
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
            print("DRY RUN MODE - Commands that would be executed:")
            print("="*60)

            for ecosystem, tools in plan.tools.items():
                print(f"\n{ecosystem.upper()} ({len(tools)} tools):")
                for tool in tools:
                    cmd = tool.get('install_cmd', 'N/A')
                    deps_ok = "✓" if tool.get("dependencies_ok", True) else "✗"

                    print(f"  [{deps_ok}] {tool['name']}")
                    print(f"      Command: {cmd}")
                    deps_hint = tool.get("dependency_hint", "")
                    if deps_hint:
                        print(f"      ⚠️  {deps_hint}")

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
        """Interactive tool selection.

        Args:
            grouped: Dict mapping ecosystem to list of tools

        Returns:
            List of selected tools
        """
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
        """Check if tool requires explicit approval.

        Args:
            tool: Tool metadata dict

        Returns:
            True if tool is high-risk
        """
        return tool.get("name", "").lower() in self.HIGH_RISK_TOOLS

    def _get_approval(self, tools: List[Dict]) -> bool:
        """Get user approval for installation.

        Args:
            tools: List of tools to approve

        Returns:
            True if user approves
        """
        tool_names = ', '.join(t['name'] for t in tools)
        choice = input(f"Approve installation of {tool_names}? [y/n]: ").lower()
        return choice == 'y'

    def _check_dependencies(self, tool: Dict) -> DependencyCheck:
        """Check if required dependencies are available.

        Args:
            tool: Tool metadata dict

        Returns:
            DependencyCheck with availability status
        """
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
                return DependencyCheck(available=True, installer_hint="pipx")
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
        """Load cached detection results if not expired. Thread-safe.

        Returns:
            Cached ToolInfo list or None if cache invalid
        """
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
        """Save detection results to cache. Thread-safe.

        Args:
            tools: List of ToolInfo to cache
        """
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
        """Record failed installation for future reference.

        Args:
            tool_name: Name of tool that failed
            error: Error result
        """
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
        """Get history of failed installations.

        Returns:
            Dict mapping tool names to failure info
        """
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

- [ ] **Step 2: Create test_manager.py**

```python
"""Test ToolManager orchestration."""

import pytest
import tempfile
import os
from unittest.mock import patch, Mock
from assistant.tools.manager import ToolManager
from assistant.tools.models import ToolStatus, ErrorCode


@pytest.fixture
def temp_yaml_file():
    """Create a temporary YAML file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_content = """
tools:
  test_tool:
    name: "test_tool"
    ecosystem: "binary"
    install_cmd: "echo test"
    version_flags:
      - "--version"
    category: "test"
    risk: "low"
    alternatives: []
    docs_url: ""
    deprecated: false
"""
        f.write(yaml_content)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def manager():
    """Create a ToolManager instance."""
    return ToolManager(cache_ttl=60)  # Short TTL for testing


def test_manager_initialization(manager):
    """Test manager initializes correctly."""
    assert manager is not None
    assert manager.core_tools is not None
    assert len(manager.core_tools) > 0
    assert manager._cache_path is not None
    assert manager._failed_installs_path is not None


def test_manager_loads_custom_tools(temp_yaml_file):
    """Test manager loads custom tools from YAML."""
    manager = ToolManager(custom_tools_path=temp_yaml_file, cache_ttl=60)
    assert "test_tool" in manager.custom_tools


def test_manager_detect(manager):
    """Test tool detection."""
    detected = manager.detect(use_cache=False)
    
    assert isinstance(detected, list)
    assert len(detected) > 0
    
    # Check that all detected items are ToolInfo
    for item in detected:
        assert item.name is not None
        assert item.status in ToolStatus


def test_manager_detect_uses_cache(manager):
    """Test detection uses cache when available."""
    # First detection
    detected1 = manager.detect(use_cache=False)
    
    # Second detection should use cache
    detected2 = manager.detect(use_cache=True)
    
    assert len(detected1) == len(detected2)


def test_manager_get_missing(manager):
    """Test getting missing tools."""
    missing = manager.get_missing()
    
    assert isinstance(missing, list)
    # All missing tools should NOT be INSTALLED or OUTDATED
    for tool in missing:
        assert tool["status"] not in [ToolStatus.INSTALLED.value, ToolStatus.OUTDATED.value]


def test_manager_get_outdated(manager):
    """Test getting outdated tools."""
    outdated = manager.get_outdated()
    
    assert isinstance(outdated, list)
    # All outdated tools should have OUTDATED status
    for tool in outdated:
        assert tool["status"] == ToolStatus.OUTDATED.value


def test_manager_is_available(manager):
    """Test checking if tool is available."""
    # python3 should always be available
    assert manager.is_available("python3") is True
    
    # Non-existent tool should not be available
    assert manager.is_available("nonexistent_tool_xyz") is False


def test_manager_is_available_case_insensitive(manager):
    """Test is_available is case-insensitive."""
    # These should all work the same
    assert manager.is_available("python3") == manager.is_available("Python3")
    assert manager.is_available("PYTHON3") == manager.is_available("python3")


def test_manager_get_tool_metadata(manager):
    """Test getting tool metadata."""
    metadata = manager._get_tool_metadata("nmap")
    
    assert metadata is not None
    assert metadata["name"] == "nmap"
    assert "ecosystem" in metadata
    assert "install_cmd" in metadata


def test_manager_get_tool_metadata_not_found(manager):
    """Test getting metadata for non-existent tool."""
    metadata = manager._get_tool_metadata("nonexistent_tool_xyz")
    
    assert metadata is None


def test_manager_custom_overrides_core(temp_yaml_file):
    """Test custom tools override core tools."""
    manager = ToolManager(custom_tools_path=temp_yaml_file, cache_ttl=60)
    
    # Add a tool with same name as core tool
    # This should override the core tool
    assert "test_tool" in manager.custom_tools


def test_manager_create_install_plan_for_tools(manager):
    """Test creating install plan for specific tools."""
    plan = manager.create_install_plan_for_tools(["nmap", "nuclei"])
    
    assert plan.total > 0
    assert "tools" in plan.tools
    assert len(plan.tools) > 0


def test_manager_create_install_plan_for_categories(manager):
    """Test creating install plan for categories."""
    plan = manager.create_install_plan_for_categories(["scanner"])
    
    assert plan.total >= 0
    assert "scanner" in plan.categories


def test_manager_update_tool_dry_run(manager):
    """Test dry run update."""
    result = manager.update_tool("nmap", dry_run=True)
    
    assert result.success is True
    assert "Dry run" in result.message


def test_manager_update_tool_not_found(manager):
    """Test updating non-existent tool."""
    result = manager.update_tool("nonexistent_tool_xyz")
    
    assert result.success is False
    assert result.code == ErrorCode.NOT_FOUND


def test_manager_update_all_dry_run(manager):
    """Test dry run update all."""
    results = manager.update_all(dry_run=True)
    
    assert isinstance(results, dict)
    # All results should be success in dry run
    for tool_name, result in results.items():
        assert result.success is True


def test_manager_check_dependencies(manager):
    """Test dependency checking."""
    # Check python3 tool (should have no dependencies)
    tool = {
        "name": "test",
        "ecosystem": "apt"
    }
    
    deps = manager._check_dependencies(tool)
    
    assert deps.available is True


def test_manager_check_dependencies_missing(manager):
    """Test dependency checking with missing dependency."""
    # Check a Go tool when go is not available
    tool = {
        "name": "test",
        "ecosystem": "go"
    }
    
    # Mock shutil.which to simulate missing go
    with patch('assistant.tools.manager.shutil.which') as mock_which:
        mock_which.return_value = None
        deps = manager._check_dependencies(tool)
    
        assert deps.available is False
        assert "go" in " ".join(deps.missing)


def test_manager_is_high_risk(manager):
    """Test high-risk tool detection."""
    high_risk_tool = {"name": "metasploit"}
    low_risk_tool = {"name": "nmap"}
    
    assert manager._is_high_risk(high_risk_tool) is True
    assert manager._is_high_risk(low_risk_tool) is False


def test_manager_group_by_ecosystem(manager):
    """Test grouping tools by ecosystem."""
    tools = [
        {"name": "nmap", "ecosystem": "apt"},
        {"name": "nuclei", "ecosystem": "go"},
        {"name": "masscan", "ecosystem": "apt"}
    ]
    
    grouped = manager._group_by_ecosystem(tools)
    
    assert "apt" in grouped
    assert "go" in grouped
    assert len(grouped["apt"]) == 2
    assert len(grouped["go"]) == 1


def test_manager_list_available(manager):
    """Test listing available tools."""
    available = manager.list_available()
    
    assert isinstance(available, list)
    # All tools should have required fields
    for tool in available:
        assert "name" in tool
        assert "status" in tool
        assert "version" in tool


def test_manager_list_available_with_category_filter(manager):
    """Test listing available tools with category filter."""
    scanner_tools = manager.list_available(category="scanner")
    
    assert isinstance(scanner_tools, list)
    # All tools should have scanner category
    for tool in scanner_tools:
        assert tool["category"] == "scanner"


def test_manager_clear_cache(manager):
    """Test cache clearing."""
    # Ensure cache exists
    manager._save_cache([])
    assert os.path.exists(manager._cache_path)
    
    # Clear cache
    manager._clear_cache()
    assert not os.path.exists(manager._cache_path)


def test_manager_cache_lock_thread_safety(manager):
    """Test that cache operations use cache lock."""
    # This is more of a structural test - we verify the lock exists
    assert manager._cache_lock is not None
    assert manager._install_lock is not None
    assert manager._cache_lock is not manager._install_lock  # Different locks


def test_manager_record_failed_install(manager):
    """Test recording failed installations."""
    from assistant.tools.models import Result, ErrorCode
    
    error = Result(
        success=False,
        code=ErrorCode.INSTALL_FAILED,
        message="Test failure"
    )
    
    manager._record_failed_install("test_tool", error)
    
    failed = manager._get_failed_installs()
    
    assert "test_tool" in failed
    assert failed["test_tool"]["message"] == "Test failure"
    assert failed["test_tool"]["retry_count"] == 1


def test_manager_get_failed_installs(manager):
    """Test getting failed installation history."""
    failed = manager._get_failed_installs()
    
    assert isinstance(failed, dict)
    # Should be empty initially or have data from previous runs
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/tools/test_manager.py -v`
Expected: All 28+ tests PASS

- [ ] **Step 4: Commit**

```bash
git add assistant/tools/manager.py tests/tools/test_manager.py
git commit -m "feat: add ToolManager with orchestration, caching, and approval guards"
```

---

## Task 9: Create ToolSelector

**Files:**
- Create: `assistant/tools/selector.py`
- Create: `tests/tools/test_selector.py`

- [ ] **Step 1: Create selector.py with AI decision layer**

```python
"""AI decision layer for tool selection based on requirements."""

from typing import List, Optional, Dict, Any
from assistant.tools.models import logger


class ToolSelector:
    """AI decision layer for tool selection based on requirements."""

    # Capability mapping with tool metadata
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

    def __init__(self, manager):
        """Initialize ToolSelector.

        Args:
            manager: ToolManager instance for checking availability
        """
        self.manager = manager
        self.capability_map = self.CAPABILITY_MAP

    def select_best_tool(self, capability: str, preference: str = "balanced") -> Optional[str]:
        """Select best tool for a capability based on preference.

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
        """Get all available tools for a capability.

        Args:
            capability: Capability name

        Returns:
            List of available tool names
        """
        if capability not in self.capability_map:
            return []

        return [t for t in self.capability_map[capability].keys()
                if self.manager.is_available(t)]

    def get_missing_tools_for_capability(self, capability: str) -> List[str]:
        """Get missing tools for a capability.

        Args:
            capability: Capability name

        Returns:
            List of missing tool names
        """
        if capability not in self.capability_map:
            return []

        return [t for t in self.capability_map[capability].keys()
                if not self.manager.is_available(t)]
```

- [ ] **Step 2: Create test_selector.py**

```python
"""Test AI tool selection logic."""

import pytest
from unittest.mock import Mock
from assistant.tools.selector import ToolSelector


@pytest.fixture
def manager():
    """Create mock ToolManager."""
    manager = Mock()
    manager.is_available.side_effect = lambda name: name in ["nmap", "python3", "nuclei", "ffuf"]
    return manager


@pytest.fixture
def selector(manager):
    """Create ToolSelector instance."""
    return ToolSelector(manager)


def test_selector_initialization(selector):
    """Test selector initializes correctly."""
    assert selector is not None
    assert selector.manager is not None
    assert selector.capability_map is not None


def test_select_best_tool_balanced(selector):
    """Test balanced tool selection (by priority)."""
    # nmap has priority 10, nuclei has priority 9
    # Both are available, so nmap should be selected
    tool = selector.select_best_tool("port_scan", "balanced")
    
    assert tool == "nmap"


def test_select_best_tool_speed(selector):
    """Test speed-based tool selection."""
    # For speed, we'd select fast tools
    # python3 is not in port_scan, so this will return None or the first available
    tool = selector.select_best_tool("port_scan", "speed")
    
    if tool:
        assert selector.manager.is_available(tool)


def test_select_best_tool_accuracy(selector):
    """Test accuracy-based tool selection."""
    tool = selector.select_best_tool("port_scan", "accuracy")
    
    if tool:
        assert selector.manager.is_available(tool)


def test_select_best_tool_unknown_capability(selector):
    """Test selection with unknown capability."""
    tool = selector.select_best_tool("unknown_capability")
    
    assert tool is None


def test_select_best_tool_no_available_tools(selector):
    """Test selection when no tools are available."""
    # Mock manager to return False for all tools
    selector.manager.is_available.return_value = False
    
    tool = selector.select_best_tool("port_scan", "balanced")
    
    assert tool is None


def test_get_tools_by_capability(selector):
    """Test getting all available tools for capability."""
    tools = selector.get_tools_by_capability("port_scan")
    
    assert isinstance(tools, list)
    # All returned tools should be available
    for tool in tools:
        assert selector.manager.is_available(tool)


def test_get_tools_by_capability_unknown(selector):
    """Test getting tools for unknown capability."""
    tools = selector.get_tools_by_capability("unknown_capability")
    
    assert tools == []


def test_get_missing_tools_for_capability(selector):
    """Test getting missing tools for capability."""
    missing = selector.get_missing_tools_for_capability("subdomain_enum")
    
    assert isinstance(missing, list)
    # All returned tools should NOT be available
    for tool in missing:
        assert not selector.manager.is_available(tool)


def test_get_missing_tools_for_capability_unknown(selector):
    """Test getting missing tools for unknown capability."""
    missing = selector.get_missing_tools_for_capability("unknown_capability")
    
    assert missing == []


def test_capability_map_structure(selector):
    """Test that capability map has correct structure."""
    for capability, tools in selector.capability_map.items():
        assert isinstance(tools, dict)
        for tool_name, metadata in tools.items():
            assert "priority" in metadata
            assert "speed" in metadata
            assert "accuracy" in metadata
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/tools/test_selector.py -v`
Expected: All 9 tests PASS

- [ ] **Step 4: Commit**

```bash
git add assistant/tools/selector.py tests/tools/test_selector.py
git commit -m "feat: add ToolSelector for AI decision layer"
```

---

## Task 10: Create Integration Tests

**Files:**
- Create: `tests/tools/integration/test_tool_management.py`

- [ ] **Step 1: Create end-to-end integration tests**

```python
"""End-to-end integration tests for tool management system."""

import pytest
import tempfile
import os
from assistant.tools.manager import ToolManager
from assistant.tools.models import ToolStatus


@pytest.fixture
def temp_custom_tools():
    """Create temporary custom tools YAML."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_content = """
tools:
  integration_test_tool:
    name: "integration_test_tool"
    binary: "python3"
    ecosystem: "pip"
    install_cmd: "pip install integration-test-tool"
    version_flags:
      - "--version"
    version_required: ">=1.0.0"
    category: "test"
    risk: "low"
    alternatives: []
    docs_url: ""
    deprecated: false
    priority: 5
    speed: "fast"
    accuracy: "medium"
"""
        f.write(yaml_content)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def manager(temp_custom_tools):
    """Create ToolManager with temporary custom tools."""
    return ToolManager(
        cache_ttl=30,  # Short TTL for testing
        custom_tools_path=temp_custom_tools
    )


def test_integration_detection_workflow(manager):
    """Test complete detection workflow."""
    # Detect all tools
    detected = manager.detect(use_cache=False)
    
    assert isinstance(detected, list)
    assert len(detected) > 0
    
    # Verify we have at least some installed tools
    installed = [t for t in detected if t.status == ToolStatus.INSTALLED]
    assert len(installed) > 0
    
    # python3 should always be installed
    python3_tools = [t for t in detected if t.name.lower() == "python3"]
    assert len(python3_tools) > 0
    assert python3_tools[0].status == ToolStatus.INSTALLED


def test_integration_missing_tools_workflow(manager):
    """Test getting missing tools workflow."""
    # Get missing tools
    missing = manager.get_missing()
    
    assert isinstance(missing, list)
    
    # All missing tools should not be installed
    for tool in missing:
        assert tool["status"] != ToolStatus.INSTALLED.value


def test_integration_custom_tools_loading(manager):
    """Test that custom tools are loaded and detected."""
    # Check that custom tool is in custom_tools
    assert "integration_test_tool" in manager.custom_tools
    
    # Detect tools
    detected = manager.detect(use_cache=False)
    tool_names = [t.name for t in detected]
    
    # Custom tool should be detected (as python3 since that's the binary)
    # Since we're using python3 as binary, it should show as installed
    assert "integration_test_tool" in tool_names


def test_integration_create_install_plan_workflow(manager):
    """Test creating install plan workflow."""
    # Create plan for a specific tool
    plan = manager.create_install_plan_for_tools(["nmap"])
    
    assert plan is not None
    assert isinstance(plan.total, int)
    assert "tools" in plan.tools
    
    # nmap is in apt ecosystem (if not installed)
    # If it's installed, total might be 0
    if plan.total > 0:
        assert any("nmap" in tools.get(ecosystem, []) 
                  for ecosystem, tools in plan.tools.items())


def test_integration_is_available_workflow(manager):
    """Test tool availability checking."""
    # python3 should be available
    assert manager.is_available("python3") is True
    
    # Random tool likely not available
    assert manager.is_available("nonexistent_tool_xyz_12345") is False


def test_integration_case_insensitive_workflow(manager):
    """Test case-insensitive operations."""
    # These should all work the same
    assert manager.is_available("python3") == manager.is_available("PYTHON3")
    assert manager.is_available("PYTHON3") == manager.is_available("Python3")
    
    # Get metadata should also be case-insensitive
    metadata1 = manager._get_tool_metadata("python3")
    metadata2 = manager._get_tool_metadata("PYTHON3")
    
    # Either both None or both not None
    assert (metadata1 is None) == (metadata2 is None)


def test_integration_cache_workflow(manager):
    """Test caching workflow."""
    # First detection (cache miss)
    detected1 = manager.detect(use_cache=False)
    assert len(detected1) > 0
    
    # Second detection (cache hit)
    detected2 = manager.detect(use_cache=True)
    assert len(detected2) == len(detected1)
    
    # Clear cache
    manager._clear_cache()
    
    # Third detection (cache miss)
    detected3 = manager.detect(use_cache=True)
    assert len(detected3) == len(detected1)


def test_integration_list_available_workflow(manager):
    """Test listing available tools."""
    available = manager.list_available()
    
    assert isinstance(available, list)
    assert len(available) > 0
    
    # All tools should have required fields
    for tool in available:
        assert "name" in tool
        assert "status" in tool
        assert "version" in tool


def test_integration_dry_run_update_workflow(manager):
    """Test dry run update workflow."""
    # Try to update python3 (always available)
    result = manager.update_tool("python3", dry_run=True)
    
    assert result.success is True
    assert "Dry run" in result.message


def test_integration_resolver_workflow(manager):
    """Test resolver integration with manager."""
    # Test that deprecated tools are handled
    # wifitex is deprecated
    detected = manager.detect(use_cache=False)
    tool_names = [t.name for t in detected]
    
    # wifitex should not be in detected (deprecated without replacement)
    assert "wifitex" not in tool_names


def test_integration_dependency_checking_workflow(manager):
    """Test dependency checking integration."""
    # Check a tool that requires Go
    tool = {
        "name": "nuclei",
        "ecosystem": "go"
    }
    
    deps = manager._check_dependencies(tool)
    
    # If go is installed, deps should be available
    # If go is not installed, deps should show go as missing
    if deps.available:
        assert "go" not in " ".join(deps.missing)
    else:
        assert "go" in " ".join(deps.missing)


def test_integration_high_risk_tool_workflow(manager):
    """Test high-risk tool handling."""
    high_risk_tool = {"name": "metasploit"}
    
    assert manager._is_high_risk(high_risk_tool) is True
    
    low_risk_tool = {"name": "nmap"}
    assert manager._is_high_risk(low_risk_tool) is False


def test_integration_install_plan_grouping(manager):
    """Test install plan grouping by ecosystem."""
    # Create plan for multiple tools from different ecosystems
    tools = ["nmap", "nuclei", "python3"]
    plan = manager.create_install_plan_for_tools(tools)
    
    if plan.total > 0:
        # Check that tools are grouped by ecosystem
        for ecosystem, tools in plan.tools.items():
            assert isinstance(tools, list)
            for tool in tools:
                assert "name" in tool
                assert "ecosystem" in tool


def test_integration_failed_install_recording(manager):
    """Test failed install recording and retrieval."""
    from assistant.tools.models import Result, ErrorCode
    
    # Record a failed install
    error = Result(
        success=False,
        code=ErrorCode.INSTALL_FAILED,
        message="Test integration failure"
    )
    
    manager._record_failed_install("test_tool", error)
    
    # Retrieve failed installs
    failed = manager._get_failed_installs()
    
    assert "test_tool" in failed
    assert failed["test_tool"]["message"] == "Test integration failure"
    assert failed["test_tool"]["retry_count"] == 1


def test_integration_version_requirement_checking(manager):
    """Test version requirement checking in detection."""
    # Check a tool that should be installed
    detected = manager.detect(use_cache=False)
    
    for tool in detected:
        if tool.status == ToolStatus.OUTDATED:
            # Should have a warning about version
            assert tool.warning is not None
            assert "version" in tool.warning.lower()


def test_integration_custom_tools_precedence(temp_custom_tools):
    """Test that custom tools override core tools."""
    # This test verifies the custom > core precedence
    manager = ToolManager(custom_tools_path=temp_custom_tools)
    
    # Check that custom tool is loaded
    assert "integration_test_tool" in manager.custom_tools
    
    # Get metadata for the custom tool
    metadata = manager._get_tool_metadata("integration_test_tool")
    
    # Should return custom tool metadata, not core
    assert metadata is not None
    assert metadata["name"] == "integration_test_tool"
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/tools/integration/test_tool_management.py -v`
Expected: All 17 integration tests PASS (may take longer due to real detection)

- [ ] **Step 3: Commit**

```bash
git add tests/tools/integration/test_tool_management.py
git commit -m "test: add end-to-end integration tests for tool management"
```

---

## Task 11: Update runner.py Imports (if needed)

**Files:**
- Modify: `assistant/tools/runner.py`

- [ ] **Step 1: Check if runner.py needs import updates**

Run: `grep -n "from assistant.tools.detector import\|from assistant.tools.models import" assistant/tools/runner.py`
Expected: May need to update imports if they reference old detector structure

- [ ] **Step 2: Update imports in runner.py if needed**

```python
# Update imports at top of runner.py if needed
# Example (modify if needed):
from assistant.tools.models import ToolInfo, ToolStatus
from assistant.tools.manager import ToolManager
```

- [ ] **Step 3: Commit if changes made**

```bash
git add assistant/tools/runner.py
git commit -m "chore: update runner.py imports for new tool system structure"
```

---

## Task 12: Update Documentation

**Files:**
- Modify: `assistant/tools/CUSTOM_TOOLS.md`
- Modify: `assistant/tools/ADDING_TOOLS.md`

- [ ] **Step 1: Update CUSTOM_TOOLS.md to reference new system**

```markdown
# Using Custom/User-Made Tools with AI Assistant (Updated)

## Overview

Your personal tools (wifitex, custom scripts, modified tools) can now be integrated through the new Tool Management System.

## Integration Methods

### Option 1: Add to custom_tools.yaml (Recommended)

Add your tools to `~/.assistant/custom_tools.yaml`:

```yaml
tools:
  my-custom-tool:
    name: "my-custom-tool"
    binary: "my-custom-tool"
    ecosystem: "binary"
    install_cmd: "cp /path/to/tool /usr/local/bin/"
    version_flags:
      - "--version"
    version_required: ">=1.0.0"
    category: "custom"
    risk: "low"
    alternatives: []
    docs_url: "https://github.com/yourusername/tool"
    deprecated: false
    priority: 5
    speed: "medium"
    accuracy: "medium"
```

### Option 2: Add to CORE_TOOLS (Advanced)

Add to `assistant/tools/metadata.py` CORE_TOOLS dict if you want it in the core catalog.

## Using Custom Tools

Once added, the AI can:
- Detect your custom tools automatically
- Include them in `/tools` list
- Integrate them into workflows
- Create install plans for capabilities

## Example Usage

```
You: install my custom scanner
AI: Creating install plan...
     BINARY: my-custom-tool
     Command: cp /path/to/tool /usr/local/bin/

Approve installation? [y/n]:
```

## Tool Metadata Schema

### Required Fields
- `name`: Tool name
- `ecosystem`: "apt", "go", "pip", "cargo", "binary", or "manual-note"
- `install_cmd`: Installation command
- `version_flags`: List of version flags to try (e.g., ["--version", "-V"])

### Optional Fields
- `binary`: Binary name (defaults to name if not specified)
- `version_required`: Version requirement (e.g., ">=3.0.0")
- `category`: Tool category
- `risk`: Risk level ("low", "medium", "high")
- `alternatives`: List of alternative tools
- `docs_url`: Documentation URL
- `deprecated`: Whether tool is deprecated
- `priority`: Priority for selection (higher = preferred)
- `speed`: Speed rating ("fast", "medium", "slow")
- `accuracy`: Accuracy rating ("high", "medium", "low")

## See Also

- [ADD_TOOLS.md](ADDING_TOOLS.md) - How to add new tools to core catalog
- [Tool Manager Design](docs/superpowers/specs/2026-04-28-tool-manager-design.md) - Full system design
```

- [ ] **Step 2: Update ADDING_TOOLS.md to reference new system**

```markdown
# Adding Tools to AI Assistant (Updated)

## Overview

The AI Assistant now has an intelligent Tool Management System with detection, installation, and lifecycle management.

## Adding Tools to Core Catalog

Add tools to `assistant/tools/metadata.py` in the CORE_TOOLS dict.

### Tool Metadata Template

```python
CORE_TOOLS = {
    "tool_name": {
        "name": "tool_name",
        "binary": "tool_name",  # defaults to name if not specified
        "ecosystem": "apt",  # apt, go, pip, cargo, binary, manual-note
        "install_cmd": "apt install tool_name",
        "version_flags": ["--version", "-V"],
        "version_required": ">=1.0.0",
        "category": "scanner",
        "risk": "medium",
        "alternatives": [],
        "docs_url": "https://tool.example.com",
        "deprecated": false,
        "priority": 10,
        "speed": "medium",
        "accuracy": "high"
    },
    # ... more tools
}
```

### Field Explanations

**Required:**
- `name`: Tool identifier
- `ecosystem`: Installation method
- `install_cmd`: Installation command
- `version_flags`: List of version detection flags to try in order

**Optional:**
- `binary`: Binary name (if different from name)
- `version_required`: Minimum version requirement
- `category`: Tool category
- `risk`: Security risk level
- `alternatives`: Alternative tools
- `docs_url`: Documentation link
- `deprecated`: Mark as deprecated
- `priority`: Selection priority (higher = preferred)
- `speed`: Performance rating
- `accuracy`: Result quality rating

### Ecosystem Examples

**APT:**
```python
"nmap": {
    "ecosystem": "apt",
    "install_cmd": "apt install nmap",
}
```

**Go:**
```python
"nuclei": {
    "ecosystem": "go",
    "install_cmd": "go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
}
```

**Pip/Pipx:**
```python
"volatility": {
    "ecosystem": "pip",
    "install_cmd": "pip install volatility",
}
```

**Cargo:**
```python
"rustscan": {
    "ecosystem": "cargo",
    "install_cmd": "cargo install rustscan",
}
```

## Testing After Adding Tools

1. **Verify detection:**
```bash
python -c "from assistant.tools.manager import ToolManager; m = ToolManager(); print([t.name for t in m.detect() if 'new_tool' in t.name.lower()])"
```

2. **Verify whitelist:**
```bash
python -c "from assistant.tools.runner import TOOL_WHITELIST; print('new_tool' in TOOL_WHITELIST)"
```

3. **Run unit tests:**
```bash
pytest tests/tools/ -v
```

## Version Detection Best Practices

### Common Version Flags

Try multiple flags in order:
- `--version` (most common)
- `-version` (Go tools)
- `-V` (many Unix tools)
- `--help` (tools without version flag)
- `-v` (some tools)

### Problematic Tools

Use overrides in `resolver.py`:
```python
BAD_VERSION_CMDS = {
    "assetfinder": ["--help"],  # doesn't support --version
    "john": ["--list=build-info"],
    "autopsy": ["-h"],
    "dirsearch": ["--help"],
}
```

## See Also

- [CUSTOM_TOOLS.md](CUSTOM_TOOLS.md) - How to add your personal/custom tools
- [Tool Manager Design](docs/superpowers/specs/2026-04-28-tool-manager-design.md) - Full system design
```

- [ ] **Step 3: Commit documentation updates**

```bash
git add assistant/tools/CUSTOM_TOOLS.md assistant/tools/ADDING_TOOLS.md
git commit -m "docs: update tool documentation for new management system"
```

---

## Task 13: Run Full Test Suite

**Files:**
- Run: All test files

- [ ] **Step 1: Run all tool management tests**

Run: `pytest tests/tools/ -v --cov=assistant/tools --cov-report=html`
Expected: All tests pass, coverage report generated

- [ ] **Step 2: Verify coverage meets targets**

Expected coverage:
- Detector: 95%+
- Resolver: 90%+
- Installer: 80%+
- Manager: 85%+
- Selector: 85%+

- [ ] **Step 3: Commit**

```bash
git add tests/tools/ coverage.html
git commit -m "test: verify all tests pass and coverage meets targets"
```

---

## Task 14: Create Example Usage Script

**Files:**
- Create: `examples/tool_manager_example.py`

- [ ] **Step 1: Create example usage script**

```python
"""Example usage of the Tool Management System."""

from assistant.tools.manager import ToolManager
from assistant.tools.selector import ToolSelector
from assistant.tools.models import logger

def main():
    """Demonstrate tool management capabilities."""
    print("="*60)
    print("Tool Management System Example")
    print("="*60)

    # Initialize manager
    manager = ToolManager()

    # Example 1: Detect all tools
    print("\n1. Detecting tools...")
    detected = manager.detect(use_cache=False)
    print(f"   Found {len(detected)} tools")
    print(f"   Installed: {len([t for t in detected if t.status.value == 'installed'])}")
    print(f"   Missing: {len([t for t in detected if t.status.value == 'not_found'])}")

    # Example 2: List available tools
    print("\n2. Available scanners:")
    scanners = [t for t in detected if t.category == "scanner"]
    for tool in scanners[:5]:  # Show first 5
        status = "✓" if tool.status.value == "installed" else "✗"
        print(f"   [{status}] {tool.name} - {tool.version}")

    # Example 3: Get missing tools
    print("\n3. Missing tools:")
    missing = manager.get_missing()
    if missing:
        for tool in missing[:5]:
            print(f"   - {tool['name']}")
    else:
        print("   All core tools installed!")

    # Example 4: Check if specific tool is available
    print("\n4. Checking tool availability:")
    tools_to_check = ["nmap", "nuclei", "sqlmap", "nonexistent_tool"]
    for tool in tools_to_check:
        available = manager.is_available(tool)
        status = "✓ Available" if available else "✗ Not found"
        print(f"   {status}: {tool}")

    # Example 5: Use ToolSelector for intelligent selection
    print("\n5. AI Tool Selection:")
    selector = ToolSelector(manager)

    best_port_scanner = selector.select_best_tool("port_scan", "balanced")
    print(f"   Best for port scan (balanced): {best_port_scanner}")

    fastest_port_scanner = selector.select_best_tool("port_scan", "speed")
    print(f"   Fastest for port scan: {fastest_port_scanner}")

    best_for_accuracy = selector.select_best_tool("vuln_scan", "accuracy")
    print(f"   Best for vuln scan (accuracy): {best_for_accuracy}")

    # Example 6: Create install plan for missing scanner tools
    print("\n6. Install plan for scanners:")
    plan = manager.create_install_plan_for_categories(["scanner"])
    print(f"   Tools to install: {plan.total}")
    for ecosystem, tools in plan.tools.items():
        print(f"   {ecosystem.upper()}: {', '.join(t['name'] for t in tools)}")

    # Example 7: Dry run update
    print("\n7. Dry run update:")
    update_plan = manager.update_all(dry_run=True)
    print(f"   Would update {len(update_plan)} tools")

    print("\n" + "="*60)
    print("Example complete!")
    print("="*60)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run example to verify it works**

Run: `python examples/tool_manager_example.py`
Expected: Output showing detection, availability checking, and tool selection

- [ ] **Step 3: Commit**

```bash
git add examples/tool_manager_example.py
git commit -m "docs: add example usage script for Tool Manager"
```

---

## Task 15: Final Integration and Cleanup

**Files:**
- All files

- [ ] **Step 1: Run full test suite one more time**

Run: `pytest tests/tools/ -v --cov=assistant/tools --cov-report=term-missing`
Expected: All tests pass, coverage meets targets

- [ ] **Step 2: Verify backward compatibility with existing tool wrappers**

Run: `python -c "from assistant.tools.runner import ToolRunner; print('ToolRunner imports successfully')"`
Expected: No import errors

- [ ] **Step 3: Check for any remaining references to old COMMON_TOOLS**

Run: `grep -r "COMMON_TOOLS" assistant/tools/ --include="*.py"`
Expected: Only in detector.py (commented out), references removed from other files

- [ ] **Step 4: Verify no circular imports**

Run: `python -c "from assistant.tools.manager import ToolManager; from assistant.tools.selector import ToolSelector; print('No circular imports')"
Expected: No circular import errors

- [ ] **Step 5: Create final summary**

Create a summary of what was built:

```markdown
# Tool Management System - Implementation Summary

## What Was Built

### Core Components
1. **models.py** - Shared dataclasses and enums (Result, ToolInfo, DependencyCheck, InstallPlan, ErrorCode, ToolStatus)
2. **metadata.py** - CORE_TOOLS catalog with 80+ curated security tools
3. **resolver.py** - Tool name resolution, aliases, deprecation handling
4. **detector.py** - Pure detection functions (refactored, no data ownership)
5. **installer.py** - Ecosystem installers (apt, go, pip, cargo, binary)
6. **manager.py** - ToolManager orchestrator with caching, locks, validation
7. **selector.py** - AI decision layer for intelligent tool selection
8. **custom_tools.yaml** - Template for user-added tools

### Key Features
- ✅ Pure detection layer (no side effects)
- ✅ Multi-ecosystem installation (apt, go, pip, cargo, binary)
- ✅ Version constraint checking with OUTDATED status
- ✅ Dependency checking before installation
- ✅ Safety guards for high-risk tools
- ✅ Cache layer with TTL (5 minutes)
- ✅ Separate locks for cache and install (no deadlock)
- ✅ Failure memory for learning from errors
- ✅ Dry-run mode for preview
- ✅ Progress callbacks for long operations
- ✅ Comprehensive logging
- ✅ PATH warnings for Go/Cargo/Pip tools
- ✅ Case-insensitive tool names
- ✅ Custom tools override core tools
- ✅ Metadata validation

### Testing
- Unit tests: models, detector, installer, manager, resolver, selector
- Integration tests: end-to-end workflows
- Coverage: 80-95%+ depending on component
- Total tests: 80+

### Documentation
- Updated CUSTOM_TOOLS.md with new system
- Updated ADDING_TOOLS.md with metadata schema
- Example usage script in examples/tool_manager_example.py
- Full design spec in docs/superpowers/specs/

## Next Steps

The tool management system is now fully functional. Users can:
1. Detect tools automatically
2. Install missing tools with approval
3. Update tools to latest versions
4. Add custom tools via YAML
5. Get intelligent tool recommendations
```

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "feat: complete Tool Management System implementation

Core components:
- models.py: Shared dataclasses and enums
- metadata.py: CORE_TOOLS catalog with 80+ tools
- resolver.py: Tool name resolution
- detector.py: Pure detection functions
- installer.py: Ecosystem installers (apt, go, pip, cargo, binary)
- manager.py: ToolManager orchestrator
- selector.py: AI decision layer
- custom_tools.yaml: User tools template

Features:
- Detection, installation, update, caching
- Safety guards, dependency checking, PATH warnings
- Dry-run mode, progress callbacks, comprehensive logging
- Custom tools override core tools

Testing:
- 80+ unit and integration tests
- 80-95%+ coverage across components

Documentation:
- Updated CUSTOM_TOOLS.md and ADDING_TOOLS.md
- Example usage script
- Full design spec

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-28-tool-manager-implementation.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints for review

**Which approach?**
