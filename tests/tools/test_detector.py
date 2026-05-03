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
        "name": "python3",
        "binary": "python3",
        "version_flags": ["--version"],
        "category": "runtime"
    }

    result = detect_tool(metadata)

    assert result.name == "python3"
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
        "name": "python3",
        "binary": "python3",
        "version_flags": ["--version"],
        "version_required": ">=3.0.0",
        "category": "runtime"
    }

    result = detect_tool(metadata)

    assert result.status == ToolStatus.INSTALLED
    assert result.warning == ""


def test_extract_version():
    """Test version extraction from various formats."""
    assert _extract_version("nmap", "nmap version 7.95 ( https://nmap.org )") == "7.95"
    assert _extract_version("nuclei", "nuclei version v3.2.4") == "3.2.4"
    assert _extract_version("python", "Python 3.11.5") == "3.11.5"
    assert _extract_version("unknown", "nothing here") == "unknown"


def test_meets_version_requirement():
    """Test version comparison logic."""
    assert _meets_version_requirement("3.2.4", ">=3.0.0") is True
    assert _meets_version_requirement("2.9.1", ">=3.0.0") is False
    assert _meets_version_requirement("unknown", ">=3.0.0") is False
