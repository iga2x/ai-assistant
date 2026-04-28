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
