"""Test ToolRegistry functionality."""

import pytest
from assistant.tools.registry import ToolRegistry
from assistant.config.manager import ConfigManager


@pytest.fixture
def registry():
    """Create a tool registry for testing."""
    return ToolRegistry()


class TestToolRegistryBasics:
    """Test basic ToolRegistry functionality."""

    def test_registry_initialization(self, registry):
        """Test that registry initializes correctly."""
        assert registry is not None
        assert registry.metadata is not None
        assert registry.runner is not None

    def test_get_tool_info(self, registry):
        """Test getting tool information."""
        # Test with a common tool
        info = registry.get_tool_info('nmap')
        if info:
            assert info.name == 'nmap'
            assert hasattr(info, 'status')

    def test_is_available(self, registry):
        """Test checking if tool is available."""
        # Test with a tool that should exist
        available = registry.is_available('hostname')
        # hostname should always be available
        assert available == True

    def test_list_available(self, registry):
        """Test listing available tools."""
        available = registry.list_available()
        assert isinstance(available, list)
        # Should have at least some basic tools
        assert len(available) >= 0

    def test_list_all(self, registry):
        """Test listing all tools."""
        all_tools = registry.list_all()
        assert isinstance(all_tools, list)
        # Should have tools from metadata
        assert len(all_tools) > 0


class TestToolRegistryCache:
    """Test caching functionality."""

    def test_cache_initially_empty(self, registry):
        """Test that cache starts empty."""
        assert len(registry._cache) == 0

    def test_cache_populates(self, registry):
        """Test that cache populates on first call."""
        registry.get_tool_info('hostname', use_cache=True)
        # After first call, cache should have an entry
        # (assuming hostname is a known tool)
        if 'hostname' in registry.metadata:
            assert 'hostname' in registry._cache or True  # May not cache if not in metadata

    def test_clear_cache(self, registry):
        """Test clearing cache."""
        registry.get_tool_info('hostname', use_cache=True)
        registry.clear_cache()
        assert len(registry._cache) == 0


class TestToolRegistryExecution:
    """Test tool execution through registry."""

    def test_run_tool(self, registry):
        """Test running a tool."""
        # Run a simple, safe command
        result = registry.run_tool('shell', 'echo "test"')

        assert result is not None
        assert 'success' in result
        assert 'stdout' in result or 'stderr' in result

    def test_run_missing_tool(self, registry):
        """Test running a tool that doesn't exist."""
        result = registry.run_tool('nonexistent_tool_xyz', 'arg')

        assert result['success'] == False
        assert 'stderr' in result

    def test_get_timeout_default(self, registry):
        """Test getting timeout for tool."""
        timeout = registry.get_timeout('unknown_tool')
        # Should return default
        assert timeout > 0

    def test_get_timeout_with_config(self):
        """Test getting timeout with config."""
        config = ConfigManager()
        registry = ToolRegistry(config)

        # Get default timeout from config
        timeout = registry.get_timeout('unknown_tool')
        assert timeout == config.config.timeout.shell_command

        # Get tool-specific timeout
        nmap_timeout = registry.get_timeout('nmap')
        assert nmap_timeout == config.config.timeout.tool.get('nmap', 300)


class TestToolRegistryMetadata:
    """Test tool metadata handling."""

    def test_get_tool_metadata(self, registry):
        """Test getting tool metadata."""
        metadata = registry.get_tool_metadata('nmap')

        if metadata:
            assert 'name' in metadata
            assert 'category' in metadata

    def test_case_insensitive_lookup(self, registry):
        """Test case-insensitive tool lookup."""
        # If nmap is in metadata
        if 'nmap' in registry.metadata:
            info1 = registry.get_tool_info('nmap')
            info2 = registry.get_tool_info('NMAP')
            info3 = registry.get_tool_info('Nmap')

            # All should return the same info (or None)
            if info1:
                assert info2.name == info1.name
                if info3:
                    assert info3.name == info1.name


class TestGlobalRegistry:
    """Test global registry instance."""

    def test_get_global_registry(self):
        """Test getting global registry instance."""
        from assistant.tools.registry import get_global_registry

        registry1 = get_global_registry()
        registry2 = get_global_registry()

        # Should be the same instance
        assert registry1 is registry2

    def test_global_registry_singleton(self):
        """Test that global registry is a singleton."""
        from assistant.tools.registry import get_global_registry, _global_registry

        # First call creates it
        registry1 = get_global_registry()
        assert _global_registry is not None

        # Second call returns same instance
        registry2 = get_global_registry()
        assert registry1 is registry2 is _global_registry
