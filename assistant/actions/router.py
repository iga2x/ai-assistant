from typing import Dict, Any, Optional
from assistant.actions.schemas import ActionRequest, ActionResult
from assistant.actions.registry import get_handler
from assistant.actions.permissions import requires_approval
from assistant.tasks.task_types import (
    NON_EXECUTABLE_INTENTS,
    READ_ONLY_INTENTS,
    EXECUTABLE_INTENTS
)

class ActionRouter:
    def __init__(self, sys_info: Any, tool_runner: Any):
        self.sys_info = sys_info
        self.tool_runner = tool_runner

    async def route(self, request: ActionRequest) -> ActionResult:
        """
        Routes the action request to the appropriate handler or tool.
        """
        # 1. Read-Only System Action
        if request.action_type == "read_only_system_action":
            handler = get_handler(request.intent)
            if handler:
                context = {"sys_info": self.sys_info}
                return handler(request.params, context)
            
        # 2. Chat Response
        if request.action_type == "chat_response":
            content = request.params.get("content", "")
            # If no content, check reasoning or steps
            if not content:
                content = request.params.get("reasoning", "")
            
            return ActionResult(
                success=True,
                output=content,
                action_type="chat_response",
                intent=request.intent
            )

        # 3. Tool Execution / Security Scan / Risky Action
        if request.action_type in ["tool_execution", "safe_local_command", "security_scan", "risky_tool_action", "approval_required_action"]:
            # These are typically multi-step or require approval.
            # The Router can provide a "dry run" or handle single-step execution if already approved.
            
            # For now, we signal that it needs to go through the Task Pipeline
            return ActionResult(
                success=True,
                output=f"Action '{request.intent}' initialized. Proceeding with execution plan.",
                action_type=request.action_type,
                intent=request.intent,
                data={"needs_pipeline": True}
            )

        # 4. Report Action
        if request.action_type == "report_action":
            return ActionResult(
                success=True,
                output="Report generation initiated.",
                action_type="report_action",
                intent=request.intent
            )

        return ActionResult(
            success=False,
            output="No handler found for this action.",
            error=f"Unknown action type '{request.action_type}' or intent '{request.intent}'",
            action_type=request.action_type,
            intent=request.intent
        )
