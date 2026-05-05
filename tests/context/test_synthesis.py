import asyncio
from assistant.analysis.synthesizer import synthesize_result
from assistant.actions.executor import ExecutionResult, StepResult
from assistant.tasks.task_types import Plan

async def test_multi_step_synthesis():
    plan = Plan(title="Network Discovery", intent="network_scan")

    result = ExecutionResult(
        success=True,
        plan_title=plan.title,
        steps=[
            StepResult(
                description="Get IP",
                command="ip addr",
                stdout="2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> state UP\n inet 192.168.10.108/24 brd 192.168.10.255 scope global eth0",
                stderr="",
                exit_code=0,
                status="completed"
            ),
            StepResult(
                description="Get Gateway",
                command="ip route",
                stdout="default via 192.168.10.1 dev eth0",
                stderr="",
                exit_code=0,
                status="completed"
            ),
            StepResult(
                description="Scan neighbors",
                command="ip neigh",
                stdout="192.168.10.1 dev eth0 lladdr 00:e0:4e:39:bf:6b REACHABLE\n192.168.10.105 dev eth0 lladdr 04:d9:f5:a1:01:10 STALE",
                stderr="",
                exit_code=0,
                status="completed"
            )
        ]
    )

    summary = await synthesize_result(plan, result)
    print(f"Summary:\n{summary}")

    # With structured format, we return the first match only
    assert "Answer:" in summary
    assert "192.168.10.108" in summary
    assert "Command / Example:" in summary
    assert "hostname -I" in summary
    assert "Details:" in summary

if __name__ == "__main__":
    asyncio.run(test_multi_step_synthesis())
    print("Integration test passed!")
