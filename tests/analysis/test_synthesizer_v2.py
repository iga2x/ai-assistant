# tests/analysis/test_synthesizer_v2.py
import pytest
from unittest.mock import AsyncMock
from assistant.analysis.synthesizer import synthesize_result
from assistant.ai.schemas import Plan, PlanStep
from assistant.actions.executor import ExecutionResult, StepResult

@pytest.mark.asyncio
async def test_synthesize_result_returns_structured_response():
    # Create a simple plan
    plan = Plan(
        title="Get IP",
        intent="task",
        risk_level="low",
        steps=[PlanStep(command="hostname -I", tool="hostname", description="Get local IP")]
    )

    # Create execution result
    result = ExecutionResult(
        success=True,
        plan_title="Get IP",
        steps=[
            StepResult(
                description="Get local IP",
                command="hostname -I",
                stdout="192.168.10.108\n",
                stderr="",
                exit_code=0,
                status="completed"
            )
        ],
        failed_steps=[],
        combined_output="192.168.10.108\n"
    )

    # Synthesize without AI router (deterministic)
    synthesis = await synthesize_result(plan, result, ai_router=None)

    # Should return a string that matches structured format
    assert synthesis is not None
    assert "Answer:" in synthesis
    assert "192.168.10.108" in synthesis
