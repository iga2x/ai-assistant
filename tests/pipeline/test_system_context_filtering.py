"""Tests for system context filtering in the orchestrator.

These tests verify the allow_system_context calculation logic.
"""
import pytest
from unittest.mock import MagicMock, Mock
from assistant.app.terminal.orchestrator import Orchestrator


class TestAllowsSystemContext:
    """Test the _allows_system_context method."""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance for testing."""
        # Mock the dependencies
        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.config = {}
        mock_sys_info = {
            'hostname': 'test-host',
            'username': 'test-user',
            'os': 'Linux'
        }

        orch = Orchestrator(mock_db, mock_config, mock_sys_info)
        return orch

    @pytest.fixture
    def mock_plan_response(self):
        """Create a mock plan response."""
        plan = Mock()
        plan.steps = []
        plan.needs_analysis = False
        plan.intent = 'test'
        plan.risk_level = 'low'

        plan_response = Mock()
        plan_response.plan = plan
        plan_response.content = "Test response"
        plan_response.reasoning = "Test reasoning"
        plan_response.action_request = None
        return plan_response

    @pytest.fixture
    def mock_execution_result(self):
        """Create a mock execution result."""
        result = Mock()
        result.success = True
        result.output = "Command output"
        result.error = None
        return result

    def test_explicit_hostname_request_allows_context(self, orchestrator, mock_plan_response, mock_execution_result):
        """User explicitly requesting hostname should allow system context."""
        user_input = "What is my hostname?"
        result = orchestrator._allows_system_context(user_input, mock_plan_response, mock_execution_result)
        assert result is True, "Explicit hostname request should allow system context"

    def test_explicit_os_request_allows_context(self, orchestrator, mock_plan_response, mock_execution_result):
        """User explicitly requesting OS should allow system context."""
        user_input = "Tell me about the operating system"
        result = orchestrator._allows_system_context(user_input, mock_plan_response, mock_execution_result)
        assert result is True, "Explicit OS request should allow system context"

    def test_explanation_only_blocks_context(self, orchestrator, mock_plan_response):
        """Pure explanation without system request should block context."""
        user_input = "Explain how TCP/IP works"
        mock_execution_result = Mock()
        mock_execution_result.success = False

        result = orchestrator._allows_system_context(user_input, mock_plan_response, mock_execution_result)
        assert result is False, "Explanation only should block system context"

    def test_execution_result_allows_context(self, orchestrator, mock_plan_response, mock_execution_result):
        """Successful execution result should allow system context."""
        user_input = "List files in current directory"
        mock_execution_result.success = True
        mock_plan_response.plan.steps = []  # No plan steps, but execution succeeded

        result = orchestrator._allows_system_context(user_input, mock_plan_response, mock_execution_result)
        assert result is True, "Successful execution should allow system context"

    def test_plan_with_steps_allows_context(self, orchestrator, mock_plan_response):
        """Plan with steps should allow system context."""
        user_input = "Check system status"
        mock_plan_response.plan.steps = [Mock(), Mock()]  # Has steps
        mock_execution_result = Mock()
        mock_execution_result.success = False

        result = orchestrator._allows_system_context(user_input, mock_plan_response, mock_execution_result)
        assert result is True, "Plan with steps should allow system context"

    def test_multiple_system_patterns(self, orchestrator, mock_plan_response, mock_execution_result):
        """Test various system info request patterns."""
        test_inputs = [
            "Show me the system info",
            "What's my IP address?",
            "find my hostname",
            "display the interface information",
            "whoami command",
            "get my username"
        ]

        for user_input in test_inputs:
            result = orchestrator._allows_system_context(user_input, mock_plan_response, mock_execution_result)
            assert result is True, f"Input '{user_input}' should allow system context"

    def test_no_system_context_allowed(self, orchestrator, mock_plan_response):
        """Test inputs that should not allow system context."""
        test_inputs = [
            "What is the capital of France?",
            "Explain quantum physics",
            "Write a poem about nature",
            "How do I cook pasta?",
            "Tell me a joke"
        ]

        mock_execution_result = Mock()
        mock_execution_result.success = False
        mock_plan_response.plan.steps = []

        for user_input in test_inputs:
            result = orchestrator._allows_system_context(user_input, mock_plan_response, mock_execution_result)
            assert result is False, f"Input '{user_input}' should not allow system context"


class TestFilterSystemContext:
    """Test the _filter_system_context method."""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance for testing."""
        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.config = {}
        mock_sys_info = {
            'hostname': 'test-host',
            'username': 'test-user',
            'os': 'Linux'
        }

        orch = Orchestrator(mock_db, mock_config, mock_sys_info)
        return orch

    def test_filter_removes_leaked_system_info(self, orchestrator):
        """Filter should remove obvious leaked system context sections."""
        content = """This is the answer.

Your current system info:
Hostname: test-host
OS: Linux
Current User: test-user
Local IP: 192.168.1.1

More content here."""

        filtered, metadata = orchestrator._filter_system_context(content, allow_system_context=False)

        assert metadata["filtered"] is True, "Should indicate filtering occurred"
        assert "Hostname: test-host" not in filtered, "Should remove leaked hostname"
        assert "OS: Linux" not in filtered, "Should remove leaked OS"
        assert "Current User: test-user" not in filtered, "Should remove leaked user"
        assert "This is the answer" in filtered, "Should preserve legitimate content"
        assert "More content here" in filtered, "Should preserve legitimate content"

    def test_filter_preserves_command_results(self, orchestrator):
        """Filter should preserve legitimate command outputs that look like system info."""
        # Simulate output from a legitimate command
        content = """Here are the network interfaces:

eth0: 192.168.1.100
wlan0: 10.0.0.50

The system has 2 active interfaces."""

        filtered, metadata = orchestrator._filter_system_context(content, allow_system_context=False)

        assert metadata["filtered"] is False, "Should not filter legitimate command output"
        assert "eth0: 192.168.1.100" in filtered, "Should preserve legitimate interface output"
        assert "wlan0: 10.0.0.50" in filtered, "Should preserve legitimate interface output"

    def test_filter_skips_when_allowed(self, orchestrator):
        """Filter should not modify content when system context is allowed."""
        content = """Your current system info:
Hostname: test-host
OS: Linux

This is the answer."""

        filtered, metadata = orchestrator._filter_system_context(content, allow_system_context=True)

        assert metadata["filtered"] is False, "Should not filter when system context is allowed"
        assert "Hostname: test-host" in filtered, "Should preserve content when allowed"
        assert "OS: Linux" in filtered, "Should preserve content when allowed"
        assert filtered == content, "Content should remain unchanged"
