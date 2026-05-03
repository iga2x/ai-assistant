"""End-to-end integration tests for tool management system."""

import pytest
import tempfile
import os
import json
from assistant.tools.manager import ToolManager
from assistant.tools.models import ToolStatus, Result, ErrorCode


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
"""
        f.write(yaml_content)
    yield f.name
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def manager(temp_custom_tools):
    """Create ToolManager with temporary custom tools."""
    m = ToolManager(
        cache_ttl=30,
        custom_tools_path=temp_custom_tools
    )
    m._clear_cache()
    return m


def test_integration_detection_workflow(manager):
    """Test complete detection workflow."""
    detected = manager.detect(use_cache=False)
    assert isinstance(detected, list)
    assert len(detected) > 0
    
    # python3 should be detected as integration_test_tool (since we used binary: python3)
    # and also as python3 (since it's in core tools)
    tool_names = [t.name for t in detected]
    assert "integration_test_tool" in tool_names
    assert "python3" in tool_names


def test_integration_is_available_workflow(manager):
    """Test tool availability checking."""
    # python3 should be available
    assert manager.is_available("python3") is True
    
    # Random tool likely not available
    assert manager.is_available("nonexistent_tool_xyz_12345") is False


def test_integration_create_install_plan_workflow(manager):
    """Test creating install plan workflow."""
    # Create plan for a tool (nmap)
    plan = manager.create_install_plan_for_tools(["nmap"])
    assert plan is not None
    assert plan.total == 1
    assert "apt" in plan.tools


def test_integration_cache_workflow(manager):
    """Test caching workflow."""
    # First detection (cache miss)
    detected1 = manager.detect(use_cache=False)
    assert len(detected1) > 0
    
    # Second detection (cache hit)
    detected2 = manager.detect(use_cache=True)
    assert len(detected1) == len(detected2)


def test_integration_failed_install_recording(manager):
    """Test failed install recording and retrieval."""
    error = Result(
        success=False,
        code=ErrorCode.INSTALL_FAILED,
        message="Test integration failure"
    )
    manager._record_failed_install("test_tool", error)
    
    failed = manager._get_failed_installs()
    assert "test_tool" in failed
    assert failed["test_tool"]["message"] == "Test integration failure"
