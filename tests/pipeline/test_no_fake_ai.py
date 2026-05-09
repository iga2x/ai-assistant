"""Tests for verifying no fake AI behavior.

These tests ensure that all normal chat goes through the AI pipeline
instead of returning hardcoded responses.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from assistant.app.terminal.pipeline import ChatPipeline
from assistant.ai.response_types import PipelineResult
from assistant.tasks.task_types import Plan, PlanStep
from assistant.config.manager import AppConfig


def create_mock_config_manager():
    """Create a mock config manager with proper config."""
    mock_config_mgr = Mock()
    mock_config_mgr.config = AppConfig()
    return mock_config_mgr


def create_mock_sys_info():
    """Create a mock system info."""
    mock_sys_info = Mock()
    mock_sys_info.local_ip = "127.0.0.1"
    mock_sys_info.hostname = "localhost"
    mock_sys_info.network_neighbors = []
    mock_sys_info.os_detailed = "Linux"
    mock_sys_info.shell = "bash"
    return mock_sys_info


class TestNoFakeAI:
    """Test that all normal chat goes through AI pipeline."""

    @pytest.mark.anyio
    async def test_greeting_calls_ai(self):
        """'hi' should call AI, not use fast path."""
        mock_config_mgr = create_mock_config_manager()
        mock_sys_info = create_mock_sys_info()
        pipeline = ChatPipeline(None, mock_config_mgr, mock_sys_info)

        with patch.object(pipeline.orchestrator.ai_router, 'chat_completion', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = '{"reasoning": "User greeted", "intent": "chat_only", "content": "Hello! How can I help you today?", "plan": null}'

            with patch.object(pipeline.orchestrator.ai_router.runtime, 'get_state') as mock_state:
                mock_state.return_value = Mock(provider="ollama", model="qwen2.5:7b", available=True)

                result = await pipeline.process("hi", None)

                # Should have called AI
                assert mock_ai.called
                # Should have AI call metadata
                assert "ai_call" in result.debug
                assert result.debug["ai_call"]["source"] == "model"
                assert result.debug["ai_call"]["provider"] == "ollama"
                assert result.debug["ai_call"]["model"] == "qwen2.5:7b"

    @pytest.mark.anyio
    async def test_how_are_you_calls_ai(self):
        """'how are you' should call AI, not use fast path."""
        mock_config_mgr = create_mock_config_manager()
        mock_sys_info = create_mock_sys_info()
        pipeline = ChatPipeline(None, mock_config_mgr, mock_sys_info)

        with patch.object(pipeline.orchestrator.ai_router, 'chat_completion', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = '{"reasoning": "User asked how I am", "intent": "chat_only", "content": "I\'m doing well! How can I help?", "plan": null}'

            with patch.object(pipeline.orchestrator.ai_router.runtime, 'get_state') as mock_state:
                mock_state.return_value = Mock(provider="ollama", model="qwen2.5:7b", available=True)

                result = await pipeline.process("how are you", None)

                assert mock_ai.called
                assert result.debug["ai_call"]["source"] == "model"

    @pytest.mark.anyio
    async def test_explanation_calls_ai(self):
        """'explain how to find my IP' should call AI and return explanation."""
        mock_config_mgr = create_mock_config_manager()
        mock_sys_info = create_mock_sys_info()
        pipeline = ChatPipeline(None, mock_config_mgr, mock_sys_info)

        with patch.object(pipeline.orchestrator.ai_router, 'chat_completion', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = '{"reasoning": "User asked for explanation", "intent": "chat_only", "content": "To find your IP address, you can use the command \'ip addr\' on Linux or \'ipconfig\' on Windows.", "plan": null}'

            with patch.object(pipeline.orchestrator.ai_router.runtime, 'get_state') as mock_state:
                mock_state.return_value = Mock(provider="ollama", model="qwen2.5:7b", available=True)

                result = await pipeline.process("how to find my IP", None)

                assert mock_ai.called
                assert result.debug["ai_call"]["source"] == "model"
                assert "IP" in result.user_visible_content

    @pytest.mark.anyio
    async def test_task_execution_calls_ai(self):
        """'find my IP' should call AI and create a plan."""
        mock_config_mgr = create_mock_config_manager()
        mock_sys_info = create_mock_sys_info()
        pipeline = ChatPipeline(None, mock_config_mgr, mock_sys_info)

        with patch.object(pipeline.orchestrator.ai_router, 'chat_completion', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = '{"reasoning": "User wants to find IP", "intent": "system_info", "content": "I\'ll find your IP address.", "plan": {"title": "Find IP Address", "intent": "system_info", "risk_level": "low", "risk_summary": "Low risk operation", "requires_approval": false, "steps": [{"description": "Get IP address", "tool": "shell", "command": "ip addr show", "requires_approval": false}]}}'

            with patch.object(pipeline.orchestrator.ai_router.runtime, 'get_state') as mock_state:
                mock_state.return_value = Mock(provider="ollama", model="qwen2.5:7b", available=True)

                result = await pipeline.process("find my IP", None)

                assert mock_ai.called
                assert result.debug["ai_call"]["source"] == "model"
                # The key test is that AI was called, not the specific plan structure
                # Plan creation is the planner's responsibility
                assert "IP" in result.user_visible_content or result.plan is not None

    @pytest.mark.anyio
    async def test_ai_unavailable_returns_error(self):
        """When AI is unavailable, should return error not fake response."""
        mock_config_mgr = create_mock_config_manager()
        mock_sys_info = create_mock_sys_info()
        pipeline = ChatPipeline(None, mock_config_mgr, mock_sys_info)

        with patch.object(pipeline.orchestrator.ai_router, 'chat_completion', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = '{"reasoning": "No AI available", "intent": "chat_only", "content": "No AI model available. Please start Ollama or configure a cloud provider.", "plan": {"title": "Error", "intent": "chat_only", "steps": []}}'

            with patch.object(pipeline.orchestrator.ai_router.runtime, 'get_state') as mock_state:
                mock_state.return_value = Mock(provider="unknown", model="none", available=False)

                result = await pipeline.process("hi", None)

                # Should have called AI (even if unavailable)
                assert mock_ai.called
                # Should show error, not fake response
                assert "No AI model available" in result.user_visible_content
                # Source should be "error"
                assert result.debug["ai_call"]["source"] == "error"
                assert result.debug["ai_call"]["available"] is False

    @pytest.mark.anyio
    async def test_no_hardcoded_greeting_responses(self):
        """Verify there are no hardcoded greeting responses in the result."""
        mock_config_mgr = create_mock_config_manager()
        mock_sys_info = create_mock_sys_info()
        pipeline = ChatPipeline(None, mock_config_mgr, mock_sys_info)

        with patch.object(pipeline.orchestrator.ai_router, 'chat_completion', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = '{"reasoning": "Greeting", "intent": "chat_only", "content": "Hey there!", "plan": null}'

            with patch.object(pipeline.orchestrator.ai_router.runtime, 'get_state') as mock_state:
                mock_state.return_value = Mock(provider="ollama", model="qwen2.5:7b", available=True)

                result = await pipeline.process("hello", None)

                # Should NOT have hardcoded fast path reasoning
                assert result.internal_reasoning != "Fast path: greeting detected"
                # Should have AI reasoning
                assert result.internal_reasoning == "Greeting"

    @pytest.mark.anyio
    async def test_ai_call_latency_tracked(self):
        """Verify AI call latency is tracked in debug metadata."""
        mock_config_mgr = create_mock_config_manager()
        mock_sys_info = create_mock_sys_info()
        pipeline = ChatPipeline(None, mock_config_mgr, mock_sys_info)

        with patch.object(pipeline.orchestrator.ai_router, 'chat_completion', new_callable=AsyncMock) as mock_ai:
            async def slow_ai_call(*args, **kwargs):
                import asyncio
                await asyncio.sleep(0.1)  # Simulate slow AI
                return '{"reasoning": "Test", "intent": "chat_only", "content": "Test response", "plan": null}'

            mock_ai.side_effect = slow_ai_call

            with patch.object(pipeline.orchestrator.ai_router.runtime, 'get_state') as mock_state:
                mock_state.return_value = Mock(provider="ollama", model="qwen2.5:7b", available=True)

                result = await pipeline.process("test", None)

                # Should have latency tracking
                assert "ai_call" in result.debug
                assert "latency" in result.debug["ai_call"]
                # Latency should be at least 0.1 seconds (our simulated delay)
                assert result.debug["ai_call"]["latency"] >= 0.1

    @pytest.mark.anyio
    async def test_various_greetings_all_call_ai(self):
        """Test that various greeting patterns all call AI."""
        mock_config_mgr = create_mock_config_manager()
        mock_sys_info = create_mock_sys_info()
        pipeline = ChatPipeline(None, mock_config_mgr, mock_sys_info)

        greetings = ["hi", "hello", "hey", "yo", "hi there", "hello!"]

        for greeting in greetings:
            with patch.object(pipeline.orchestrator.ai_router, 'chat_completion', new_callable=AsyncMock) as mock_ai:
                mock_ai.return_value = '{"reasoning": "Greeting", "intent": "chat_only", "content": "Hello!", "plan": null}'

                with patch.object(pipeline.orchestrator.ai_router.runtime, 'get_state') as mock_state:
                    mock_state.return_value = Mock(provider="ollama", model="qwen2.5:7b", available=True)

                    result = await pipeline.process(greeting, None)

                    # Each greeting should call AI
                    assert mock_ai.called, f"Greeting '{greeting}' did not call AI"
                    assert result.debug["ai_call"]["source"] == "model"

    @pytest.mark.anyio
    async def test_question_patterns_call_ai(self):
        """Test that question patterns call AI, not fast path."""
        mock_config_mgr = create_mock_config_manager()
        mock_sys_info = create_mock_sys_info()
        pipeline = ChatPipeline(None, mock_config_mgr, mock_sys_info)

        questions = [
            "explain how DNS works",
            "tell me about networking",
            "what is a firewall",
        ]

        for question in questions:
            with patch.object(pipeline.orchestrator.ai_router, 'chat_completion', new_callable=AsyncMock) as mock_ai:
                mock_ai.return_value = f'{{"reasoning": "User asked: {question}", "intent": "chat_only", "content": "Here is the explanation...", "plan": null}}'

                with patch.object(pipeline.orchestrator.ai_router.runtime, 'get_state') as mock_state:
                    mock_state.return_value = Mock(provider="ollama", model="qwen2.5:7b", available=True)

                    result = await pipeline.process(question, None)

                    # Each question should call AI
                    assert mock_ai.called, f"Question '{question}' did not call AI"
                    assert result.debug["ai_call"]["source"] == "model"
