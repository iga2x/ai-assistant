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
    # nmap has priority 10, masscan has priority 8
    # Both are available (nmap is, masscan is not in mock), so nmap should be selected
    tool = selector.select_best_tool("port_scan", "balanced")
    assert tool == "nmap"


def test_select_best_tool_speed(selector):
    """Test speed-based tool selection."""
    # In port_scan: nmap (medium), masscan (fast), rustscan (fast)
    # Only nmap is available in mock
    tool = selector.select_best_tool("port_scan", "speed")
    assert tool == "nmap"


def test_get_tools_by_capability(selector):
    """Test getting all available tools for capability."""
    tools = selector.get_tools_by_capability("port_scan")
    assert isinstance(tools, list)
    assert "nmap" in tools


def test_get_missing_tools_for_capability(selector):
    """Test getting missing tools for capability."""
    missing = selector.get_missing_tools_for_capability("port_scan")
    assert "masscan" in missing
    assert "rustscan" in missing
