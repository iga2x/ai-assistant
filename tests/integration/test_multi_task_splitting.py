"""Test multi-task splitting in Orchestrator (Issue 6 fix)."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from assistant.app.terminal.orchestrator import Orchestrator


class TestMultiTaskSplitting:
    """Test that multi-task inputs are properly split and processed."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator for testing."""
        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.config = MagicMock()
        mock_sys_info = MagicMock()

        orchestrator = Orchestrator(mock_db, mock_config, mock_sys_info)

        # Mock the AI router to return simple responses
        orchestrator.ai_router.chat_completion = AsyncMock(
            return_value='{"reasoning": "test", "intent": "chat", "content": "test response"}'
        )

        # Mock other components
        orchestrator.memory.auto_extract = MagicMock()
        orchestrator.memory.entities.list_all = MagicMock(return_value=[])
        orchestrator.memory.get_all_facts = MagicMock(return_value={})
        orchestrator.context_resolver.resolve = MagicMock(side_effect=lambda x: x)

        return orchestrator

    def test_split_multi_task_comma(self, mock_orchestrator):
        """Test splitting comma-separated tasks."""
        tasks = "find my ip, scan it"
        result = mock_orchestrator._split_multi_task(tasks)

        assert len(result) == 2
        assert result[0] == "find my ip"
        assert result[1] == "scan it"

    def test_split_multi_task_and(self, mock_orchestrator):
        """Test splitting 'and' separated tasks."""
        tasks = "find my ip and scan it"
        result = mock_orchestrator._split_multi_task(tasks)

        assert len(result) == 2
        assert result[0] == "find my ip"
        assert result[1] == "scan it"

    def test_split_multi_task_then(self, mock_orchestrator):
        """Test splitting 'then' separated tasks."""
        tasks = "scan localhost then save result"
        result = mock_orchestrator._split_multi_task(tasks)

        assert len(result) == 2
        assert result[0] == "scan localhost"
        assert result[1] == "save result"

    def test_split_multi_task_multiple_commas(self, mock_orchestrator):
        """Test splitting multiple comma-separated tasks."""
        tasks = "find ip, scan it, save result"
        result = mock_orchestrator._split_multi_task(tasks)

        assert len(result) == 3
        assert result[0] == "find ip"
        assert result[1] == "scan it"
        assert result[2] == "save result"

    def test_split_single_task(self, mock_orchestrator):
        """Test that single task is not split."""
        tasks = "scan 192.168.1.1"
        result = mock_orchestrator._split_multi_task(tasks)

        assert len(result) == 1
        assert result[0] == "scan 192.168.1.1"

    def test_split_trailing_comma(self, mock_orchestrator):
        """Test that trailing comma doesn't create empty task."""
        tasks = "scan it,"
        result = mock_orchestrator._split_multi_task(tasks)

        assert len(result) == 1
        assert result[0] == "scan it"

    def test_split_empty_tasks_filtered(self, mock_orchestrator):
        """Test that empty tasks are filtered out."""
        tasks = "find ip, , scan it"
        result = mock_orchestrator._split_multi_task(tasks)

        assert len(result) == 2
        assert result[0] == "find ip"
        assert result[1] == "scan it"


class TestMultiTaskProcessing:
    """Test that multi-tasks are processed separately and results combined."""

    @pytest.fixture
    def mock_orchestrator_with_plans(self):
        """Create a mock orchestrator that returns plans."""
        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.config = MagicMock()
        mock_sys_info = MagicMock()

        orchestrator = Orchestrator(mock_db, mock_config, mock_sys_info)

        # Mock the AI router to return plan responses
        plan_response = '''{
            "reasoning": "test",
            "intent": "local_info",
            "action_type": "read_only_local",
            "content": "IP: 192.168.1.1",
            "plan": {
                "title": "Get IP",
                "intent": "local_info",
                "risk_level": "low",
                "steps": [{"description": "Get IP", "command": "hostname -I", "requires_approval": false}]
            }
        }'''

        orchestrator.ai_router.chat_completion = AsyncMock(return_value=plan_response)

        # Mock other components
        orchestrator.memory.auto_extract = MagicMock()
        orchestrator.memory.entities.list_all = MagicMock(return_value=[])
        orchestrator.memory.get_all_facts = MagicMock(return_value={})
        orchestrator.context_resolver.resolve = MagicMock(side_effect=lambda x: x)

        return orchestrator

    def test_process_multi_task_combines_results(self, mock_orchestrator_with_plans):
        """Test that multi-task processing combines all results."""
        import asyncio

        sub_tasks = ["find my ip", "scan it"]

        # Mock the single task processor
        async def mock_process_single(task, conv_id, conv_service):
            return {
                "output": f"Result for: {task}",
                "plan": None,
                "reasoning": f"Processed {task}",
                "action_request": None,
                "status": "completed"
            }

        mock_orchestrator_with_plans._process_single_task = mock_process_single

        result = asyncio.run(mock_orchestrator_with_plans._process_multi_task(
            sub_tasks, "original input", None, None
        ))

        assert result["status"] == "completed"
        assert "Task 1: find my ip" in result["output"]
        assert "Task 2: scan it" in result["output"]
        assert "Result for: find my ip" in result["output"]
        assert "Result for: scan it" in result["output"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
