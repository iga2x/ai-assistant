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
