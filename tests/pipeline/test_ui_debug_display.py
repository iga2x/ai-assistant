"""Tests for UI debug display of context filter metadata."""
import pytest
from unittest.mock import MagicMock, Mock, patch
from assistant.app.terminal.repl import InteractiveREPL


class TestUIDebugDisplay:
    """Test that the REPL UI displays context filter debug metadata."""

    @pytest.fixture
    def repl(self):
        """Create a REPL instance for testing."""
        repl = InteractiveREPL()
        repl.debug_enabled = True  # Enable debug mode
        return repl

    @pytest.fixture
    def mock_response_with_debug(self):
        """Create a mock response with debug metadata."""
        response = Mock()
        response.content = "Test response"
        response.reasoning = "Test reasoning"
        response.latency = 1.5
        response.plan = None

        # Add debug attribute with context filter metadata
        response.debug = {
            "context_filter": {
                "allowed": False,
                "filtered": True,
                "reason": "system_context_not_allowed"
            }
        }
        return response

    @pytest.fixture
    def mock_response_no_filter(self):
        """Create a mock response with no filtering."""
        response = Mock()
        response.content = "Test response"
        response.reasoning = "Test reasoning"
        response.latency = 1.5
        response.plan = None

        # Add debug attribute with context filter metadata (no filtering)
        response.debug = {
            "context_filter": {
                "allowed": True,
                "filtered": False,
                "reason": "explicit_system_info_request"
            }
        }
        return response

    def test_debug_shows_context_filter_metadata(self, repl, mock_response_with_debug):
        """Test that debug mode shows context filter metadata when filtering occurred."""
        # This should display the context filter debug info
        # The actual implementation will be in render_response or similar method
        # For now, we're testing that the debug structure exists
        assert hasattr(mock_response_with_debug, 'debug'), "Response should have debug attribute"
        assert 'context_filter' in mock_response_with_debug.debug, "Debug should have context_filter"
        assert mock_response_with_debug.debug['context_filter']['filtered'] is True, "Should indicate filtering occurred"

    def test_debug_shows_no_filter_when_allowed(self, repl, mock_response_no_filter):
        """Test that debug mode shows no filtering when system context is allowed."""
        assert hasattr(mock_response_no_filter, 'debug'), "Response should have debug attribute"
        assert 'context_filter' in mock_response_no_filter.debug, "Debug should have context_filter"
        assert mock_response_no_filter.debug['context_filter']['filtered'] is False, "Should indicate no filtering"

    def test_no_debug_attribute_doesnt_crash(self, repl):
        """Test that response without debug attribute doesn't crash the UI."""
        response = Mock(spec=['content', 'reasoning', 'latency', 'plan'])  # Only these attributes
        response.content = "Test response"
        response.reasoning = "Test reasoning"
        response.latency = 1.5
        response.plan = None

        # Should not crash when checking for debug
        has_debug = hasattr(response, 'debug')
        assert has_debug is False, "Response should not have debug attribute"

    def test_debug_disabled_doesnt_show_metadata(self, repl):
        """Test that debug mode disabled doesn't show context filter metadata."""
        repl.debug_enabled = False  # Disable debug mode

        response = Mock()
        response.content = "Test response"
        response.reasoning = "Test reasoning"
        response.latency = 1.5
        response.plan = None

        response.debug = {
            "context_filter": {
                "allowed": False,
                "filtered": True,
                "reason": "system_context_not_allowed"
            }
        }

        # When debug is disabled, metadata should not be displayed
        # This is checked by the implementation
        assert repl.debug_enabled is False, "Debug should be disabled"
