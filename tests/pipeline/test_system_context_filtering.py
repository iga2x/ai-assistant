"""Tests for system context filtering in the orchestrator.

These tests verify the allow_system_context calculation logic.
"""
import pytest
from unittest.mock import MagicMock, Mock, patch
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
        """Filter should not modify direct answers when system context is allowed, but still filter headers."""
        # When context is allowed, direct answers should be preserved
        # But obvious leaked headers should still be filtered
        content = """Your hostname is: test-host
OS: Linux

This is the answer."""

        filtered, metadata = orchestrator._filter_system_context(content, allow_system_context=True)

        assert metadata["filtered"] is False, "Should not filter direct answers when system context is allowed"
        assert "hostname is: test-host" in filtered, "Should preserve direct answers when allowed"
        assert "OS: Linux" in filtered, "Should preserve direct answers when allowed"
        assert "This is the answer" in filtered, "Should preserve direct answers when allowed"


class TestEndToEndFiltering:
    """Test end-to-end system context filtering in orchestrator flow."""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance for integration testing."""
        from assistant.config.manager import AppConfig

        mock_db = MagicMock()
        mock_config_mgr = MagicMock()
        mock_config_mgr.config = AppConfig()

        mock_sys_info = MagicMock()
        mock_sys_info.hostname = 'test-host'
        mock_sys_info.username = 'test-user'
        mock_sys_info.os = 'Linux'
        mock_sys_info.network_neighbors = []

        orch = Orchestrator(mock_db, mock_config_mgr, mock_sys_info)
        return orch

    @pytest.mark.anyio
    async def test_explanation_only_no_system_context(self, orchestrator):
        """Pure explanation request should filter out any leaked system context."""
        user_input = "Explain how TCP/IP works"
        conversation_id = None

        # Mock the AI router and planner to return predictable responses
        with patch.object(orchestrator.ai_router, 'chat_completion') as mock_ai, \
             patch.object(orchestrator.planner, 'create_plan') as mock_planner:

            # Mock the AI response to include leaked system context
            leaked_response = """TCP/IP is a suite of protocols...

Your current system info:
Hostname: test-host
OS: Linux
Current User: test-user

TCP/IP consists of four layers..."""

            mock_ai_response = MagicMock()
            mock_ai_response.content = leaked_response
            mock_ai_response.reasoning = "User asked about TCP/IP"
            mock_ai_response.action_type = "chat"

            mock_ai.return_value = mock_ai_response

            # Mock the planner
            mock_plan = MagicMock()
            mock_plan.steps = []  # No steps means it's a chat response
            mock_plan.needs_analysis = False
            mock_plan.intent = 'chat'
            mock_plan.risk_level = 'low'

            mock_plan_response = MagicMock()
            mock_plan_response.plan = mock_plan
            mock_plan_response.content = leaked_response
            mock_plan_response.reasoning = "User asked about TCP/IP"
            mock_plan_response.action_request = None

            mock_planner.return_value = mock_plan_response

            result = await orchestrator.run(user_input, conversation_id)

            # Verify the response was filtered
            assert "Hostname: test-host" not in result["output"], "Should filter leaked hostname"
            assert "OS: Linux" not in result["output"], "Should filter leaked OS"
            assert "Current User: test-user" not in result["output"], "Should filter leaked user"
            assert "TCP/IP is a suite of protocols" in result["output"], "Should preserve the explanation"

    @pytest.mark.anyio
    async def test_explicit_request_shows_context(self, orchestrator):
        """Explicit system info request should preserve system context in response."""
        user_input = "What is my hostname?"
        conversation_id = None

        # Mock the AI router and planner
        with patch.object(orchestrator.ai_router, 'chat_completion') as mock_ai, \
             patch.object(orchestrator.planner, 'create_plan') as mock_planner:

            # Mock the AI response to include system context
            system_response = """Your hostname is: test-host
OS: Linux
Current User: test-user"""

            mock_ai_response = MagicMock()
            mock_ai_response.content = system_response
            mock_ai_response.reasoning = "User asked about hostname"
            mock_ai_response.action_type = "chat"

            mock_ai.return_value = mock_ai_response

            # Mock the planner
            mock_plan = MagicMock()
            mock_plan.steps = []
            mock_plan.needs_analysis = False
            mock_plan.intent = 'chat'
            mock_plan.risk_level = 'low'

            mock_plan_response = MagicMock()
            mock_plan_response.plan = mock_plan
            mock_plan_response.content = system_response
            mock_plan_response.reasoning = "User asked about hostname"
            mock_plan_response.action_request = None

            mock_planner.return_value = mock_plan_response

            result = await orchestrator.run(user_input, conversation_id)

            # Verify the response was NOT filtered
            assert "test-host" in result["output"], "Should preserve hostname when explicitly requested"
            assert "Linux" in result["output"], "Should preserve OS when in response"
            assert "test-user" in result["output"], "Should preserve user when in response"

    @pytest.mark.anyio
    async def test_wifi_explanation_no_system_context_leak(self, orchestrator):
        """WiFi explanation questions must not leak system context."""
        user_input = "how to check wifi info and on off monitor mode"
        conversation_id = None

        # Mock the AI router and planner to return predictable responses
        with patch.object(orchestrator.ai_router, 'chat_completion') as mock_ai, \
             patch.object(orchestrator.planner, 'create_plan') as mock_planner:

            # Mock the AI response to include leaked system context
            leaked_response = """To check WiFi information and toggle monitor mode, you can use the following commands:

Your current system info:
Hostname: test-host
OS: Linux
Current User: test-user
Local IP: 192.168.1.1

Use `iwconfig` to check wireless interfaces.
Use `nmcli device wifi` to list available networks."""

            mock_ai_response = MagicMock()
            mock_ai_response.content = leaked_response
            mock_ai_response.reasoning = "User asked about WiFi monitor mode"
            mock_ai_response.action_type = "chat"

            mock_ai.return_value = mock_ai_response

            # Mock the planner
            mock_plan = MagicMock()
            mock_plan.steps = []  # No steps means it's a chat response
            mock_plan.needs_analysis = False
            mock_plan.intent = 'chat'
            mock_plan.risk_level = 'low'

            mock_plan_response = MagicMock()
            mock_plan_response.plan = mock_plan
            mock_plan_response.content = leaked_response
            mock_plan_response.reasoning = "User asked about WiFi monitor mode"
            mock_plan_response.action_request = None

            mock_planner.return_value = mock_plan_response

            result = await orchestrator.run(user_input, conversation_id)

            # Verify all required system context sections were removed
            assert "Your current system info:" not in result["output"], "Should remove system info header"
            assert "Hostname: test-host" not in result["output"], "Should remove leaked hostname"
            assert "OS: Linux" not in result["output"], "Should remove leaked OS"
            assert "Current User: test-user" not in result["output"], "Should remove leaked username"
            assert "Local IP: 192.168.1.1" not in result["output"], "Should remove leaked local IP"

            # Verify WiFi guidance is preserved
            assert "iwconfig" in result["output"], "Should preserve WiFi command guidance"
            assert "nmcli device wifi" in result["output"], "Should preserve WiFi network list command"
            assert "monitor mode" in result["output"], "Should preserve monitor mode context"
            assert "check WiFi information" in result["output"], "Should preserve WiFi information guidance"

            # Verify filtering metadata indicates filtering occurred
            assert result["debug"]["context_filter"]["filtered"] is True, "Should indicate filtering occurred"
            assert result["debug"]["context_filter"]["allowed"] is False, "System context should not be allowed"

    @pytest.mark.anyio
    async def test_find_ip_shows_result_from_execution(self, orchestrator):
        """IP finding shows IP only when appropriate (execution result, not system context)."""
        conversation_id = None

        # Test scenario 1: Without execution - IP from system context should be filtered
        user_input_no_exec = "find my IP"

        with patch.object(orchestrator.ai_router, 'chat_completion') as mock_ai, \
             patch.object(orchestrator.planner, 'create_plan') as mock_planner:

            # Mock AI response with leaked IP from system context
            leaked_ip_response = """Your IP address is 192.168.1.1.

Your current system info:
Hostname: test-host
OS: Linux
Local IP: 192.168.1.1"""

            mock_ai_response = MagicMock()
            mock_ai_response.content = leaked_ip_response
            mock_ai_response.reasoning = "User asked to find IP"
            mock_ai_response.action_type = "chat"

            mock_ai.return_value = mock_ai_response

            # Mock planner with no execution
            mock_plan = MagicMock()
            mock_plan.steps = []
            mock_plan.needs_analysis = False
            mock_plan.intent = 'chat'
            mock_plan.risk_level = 'low'

            mock_plan_response = MagicMock()
            mock_plan_response.plan = mock_plan
            mock_plan_response.content = leaked_ip_response
            mock_plan_response.reasoning = "User asked to find IP"
            mock_plan_response.action_request = None

            mock_planner.return_value = mock_plan_response

            result_no_exec = await orchestrator.run(user_input_no_exec, conversation_id)

            # IP should be filtered when it comes from system context (no execution)
            # However, since "find my IP" explicitly requests IP, it should be preserved
            # The key difference is whether it's in a leaked system context section
            assert "Your current system info:" not in result_no_exec["output"], "Should remove system info header"
            assert "Hostname: test-host" not in result_no_exec["output"], "Should remove leaked hostname"
            assert "Local IP: 192.168.1.1" not in result_no_exec["output"], "Should remove IP in system context section"

        # Test scenario 2: With execution - IP from command result should be shown
        user_input_with_exec = "find my IP"

        with patch.object(orchestrator.ai_router, 'chat_completion') as mock_ai, \
             patch.object(orchestrator.planner, 'create_plan') as mock_planner:

            # Mock AI response with IP from legitimate command execution
            execution_ip_response = """Here is your IP information:

eth0: 192.168.1.100
wlan0: 10.0.0.50

Your local IP address is 192.168.1.100."""

            mock_ai_response = MagicMock()
            mock_ai_response.content = execution_ip_response
            mock_ai_response.reasoning = "User asked to find IP - command executed"
            mock_ai_response.action_type = "chat"

            mock_ai.return_value = mock_ai_response

            # Mock planner with execution (plan has steps)
            mock_step = MagicMock()
            mock_step.command = "ip addr show"
            mock_step.description = "Get IP address"

            mock_plan = MagicMock()
            mock_plan.steps = [mock_step]  # Has steps = execution occurred
            mock_plan.needs_analysis = False
            mock_plan.intent = 'system_info'
            mock_plan.risk_level = 'low'

            mock_plan_response = MagicMock()
            mock_plan_response.plan = mock_plan
            mock_plan_response.content = execution_ip_response
            mock_plan_response.reasoning = "User asked to find IP - command executed"
            mock_plan_response.action_request = None

            mock_planner.return_value = mock_plan_response

            result_with_exec = await orchestrator.run(user_input_with_exec, conversation_id)

            # IP should be preserved when it comes from command execution
            assert "192.168.1.100" in result_with_exec["output"], "Should preserve IP from execution result"
            assert "eth0: 192.168.1.100" in result_with_exec["output"], "Should preserve interface IP from execution"
            assert "wlan0: 10.0.0.50" in result_with_exec["output"], "Should preserve all IPs from execution"

            # Verify filtering metadata indicates no filtering occurred
            assert result_with_exec["debug"]["context_filter"]["allowed"] is True, "System context should be allowed with execution"
            assert result_with_exec["debug"]["context_filter"]["filtered"] is False, "Should not filter when execution occurred"

    @pytest.mark.anyio
    async def test_filter_preserves_nmap_command_results(self, orchestrator):
        """Legitimate nmap command results must not be filtered (avoids false positives)."""
        user_input = "scan the network"
        conversation_id = None

        # Mock the AI router and planner to return predictable responses
        with patch.object(orchestrator.ai_router, 'chat_completion') as mock_ai, \
             patch.object(orchestrator.planner, 'create_plan') as mock_planner:

            # Mock the AI response to include nmap scan results
            nmap_response = """Network scan completed.

Starting Nmap 7.94 ( https://nmap.org )
Nmap scan report for 192.168.1.1
Host is up (0.0023s latency).
PORT     STATE SERVICE
22/tcp   open  ssh
80/tcp   open  http
443/tcp  open  https

Nmap scan report for 192.168.1.100
Host is up (0.0015s latency).
PORT     STATE SERVICE
3306/tcp open  mysql

Scan complete. 2 hosts up."""

            mock_ai_response = MagicMock()
            mock_ai_response.content = nmap_response
            mock_ai_response.reasoning = "User requested network scan"
            mock_ai_response.action_type = "chat"

            mock_ai.return_value = mock_ai_response

            # Mock the planner with execution
            mock_step = MagicMock()
            mock_step.command = "nmap -sn 192.168.1.0/24"
            mock_step.description = "Scan network for hosts"

            mock_plan = MagicMock()
            mock_plan.steps = [mock_step]  # Has steps = execution occurred
            mock_plan.needs_analysis = False
            mock_plan.intent = 'network_scan'
            mock_plan.risk_level = 'medium'

            mock_plan_response = MagicMock()
            mock_plan_response.plan = mock_plan
            mock_plan_response.content = nmap_response
            mock_plan_response.reasoning = "User requested network scan"
            mock_plan_response.action_request = None

            mock_planner.return_value = mock_plan_response

            result = await orchestrator.run(user_input, conversation_id)

            # Verify nmap scan results are preserved (not filtered)
            assert "Starting Nmap 7.94" in result["output"], "Should preserve nmap header"
            assert "192.168.1.1" in result["output"], "Should preserve IP addresses from scan"
            assert "192.168.1.100" in result["output"], "Should preserve all IPs from scan"
            assert "PORT     STATE SERVICE" in result["output"], "Should preserve scan output structure"
            assert "22/tcp   open  ssh" in result["output"], "Should preserve port scan results"
            assert "80/tcp   open  http" in result["output"], "Should preserve http port result"
            assert "443/tcp  open  https" in result["output"], "Should preserve https port result"
            assert "3306/tcp open  mysql" in result["output"], "Should preserve mysql port result"
            assert "Scan complete. 2 hosts up" in result["output"], "Should preserve scan summary"

            # Verify filtering metadata indicates no filtering occurred
            assert result["debug"]["context_filter"]["filtered"] is False, "Should not filter command execution results"
            assert result["debug"]["context_filter"]["allowed"] is True, "System context should be allowed with execution"
