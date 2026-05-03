"""Test ToolManager orchestration."""

import pytest
import tempfile
import os
import json
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
"""
        f.write(yaml_content)
    yield f.name
    os.unlink(f.name)


@pytest.fixture
def manager():
    """Create a ToolManager instance."""
    m = ToolManager(cache_ttl=60)
    m._clear_cache()
    return m


def test_manager_initialization(manager):
    """Test manager initializes correctly."""
    assert manager is not None
    assert manager.core_tools is not None
    assert len(manager.core_tools) > 0


def test_manager_loads_custom_tools(temp_yaml_file):
    """Test manager loads custom tools from YAML."""
    manager = ToolManager(custom_tools_path=temp_yaml_file, cache_ttl=60)
    assert "test_tool" in manager.custom_tools


def test_manager_detect(manager):
    """Test tool detection."""
    detected = manager.detect(use_cache=False)
    assert isinstance(detected, list)
    assert len(detected) > 0


def test_manager_is_available(manager):
    """Test checking if tool is available."""
    # python3 should always be available
    assert manager.is_available("python3") is True
    assert manager.is_available("nonexistent_tool_xyz") is False


def test_manager_get_tool_metadata(manager):
    """Test getting tool metadata."""
    metadata = manager._get_tool_metadata("nmap")
    assert metadata is not None
    assert metadata["name"] == "nmap"


def test_manager_create_install_plan_for_tools(manager):
    """Test creating install plan for specific tools."""
    plan = manager.create_install_plan_for_tools(["nmap", "nuclei"])
    assert plan.total == 2
    assert "apt" in plan.tools or "go" in plan.tools


def test_manager_update_tool_dry_run(manager):
    """Test dry run update."""
    result = manager.update_tool("nmap", dry_run=True)
    assert result.success is True
    assert "Dry run" in result.message


def test_manager_check_dependencies(manager):
    """Test dependency checking."""
    tool = {"name": "test", "ecosystem": "apt"}
    deps = manager._check_dependencies(tool)
    assert deps.available is True


def test_manager_record_failed_install(manager):
    """Test recording failed installations."""
    from assistant.tools.models import Result, ErrorCode
    error = Result(success=False, code=ErrorCode.INSTALL_FAILED, message="Test failure")
    manager._record_failed_install("test_tool", error)
    failed = manager._get_failed_installs()
    assert "test_tool" in failed
    assert failed["test_tool"]["message"] == "Test failure"
