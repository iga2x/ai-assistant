"""Test tool discovery unification (Issue 14 fix)."""

import pytest
from assistant.tools.registry import ToolRegistry
from assistant.tools.manager import ToolManager
from assistant.tools.detector import detect_tool


class TestToolDiscoveryUnification:
    """Test that tool discovery uses the correct interface."""

    def test_registry_is_main_interface(self):
        """Test that ToolRegistry is the main interface for discovery."""
        registry = ToolRegistry()

        # Registry should be able to list available tools
        result = registry.list_available()

        assert result is not None
        assert isinstance(result, list)

    def test_manager_for_lifecycle_only(self):
        """Test that ToolManager is for lifecycle operations."""
        manager = ToolManager()

        # Manager should have install/update methods (not direct execute)
        assert hasattr(manager, 'create_install_plan_for_tools')
        assert hasattr(manager, 'update_tool')

    def test_detector_is_internal(self):
        """Test that detector is a low-level internal function."""
        # detector should be a function, not a class
        assert callable(detect_tool)
        
        # detector requires metadata dict (internal use)
        metadata = {
            "name": "test_tool",
            "binary": "ls"  # Use a common tool for testing
        }
        
        result = detect_tool(metadata)
        
        assert result is not None
        assert hasattr(result, 'name')

    def test_registry_uses_detector_internally(self):
        """Test that Registry uses Detector internally."""
        registry = ToolRegistry()

        # Registry should have access to detector functionality
        # through its list_available method
        result = registry.list_available()

        # Should return tool info similar to what detector creates
        assert isinstance(result, list)
        if result:
            # Each tool should have the structure that detector creates
            for tool in result:
                assert hasattr(tool, 'name')
                assert hasattr(tool, 'status')

    def test_registry_can_execute_tools(self):
        """Test that Registry can execute tools (main interface)."""
        registry = ToolRegistry()

        # Registry should have run_tool method (execution interface)
        assert hasattr(registry, 'run_tool')

    def test_deprecation_warnings_present(self):
        """Test that appropriate deprecation warnings are in place."""
        import inspect
        from assistant.tools import manager, detector, registry
        
        # Check manager docstring mentions deprecation
        manager_doc = manager.__doc__
        assert "DEPRECATED" in manager_doc or "use ToolRegistry" in manager_doc
        
        # Check detector docstring mentions internal use
        detector_doc = detector.__doc__
        assert "INTERNAL" in detector_doc or "internal use" in detector_doc
        
        # Check registry docstring mentions it's the main interface
        registry_doc = registry.__doc__
        assert "MAIN INTERFACE" in registry_doc or "main interface" in registry_doc


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
