import json
from typing import List, Dict, Optional, Any
from assistant.db.database import DatabaseManager
from assistant.tasks.task_types import (
    Plan, PlanStep, PlanResponse, 
    NON_EXECUTABLE_INTENTS, EXECUTABLE_INTENTS,
    READ_ONLY_INTENTS, CONFIRMATION_INTENTS
)
from assistant.actions.schemas import ActionRequest

class Planner:
    def __init__(self, db: DatabaseManager, system_info: Optional[Any] = None):
        self.db = db
        self.system_info = system_info

    def create_plan(self, ai_output: str, user_input: str) -> PlanResponse:
        """
        Converts AI output into a PlanResponse.
        Following Phase 3 rules: Chat vs Action Routing.
        """
        try:
            # Try to parse as JSON
            data = json.loads(ai_output)
            
            # 1. Classification & Routing
            intent = data.get("intent", data.get("plan", {}).get("intent", "chat_only"))
            
            # Determine Action Type
            action_type = "chat_response"
            if intent in READ_ONLY_INTENTS:
                action_type = "read_only_system_action"
            elif intent in EXECUTABLE_INTENTS:
                action_type = "approval_required_action"
            elif intent in CONFIRMATION_INTENTS:
                action_type = "confirmation_action"

            # Create ActionRequest
            action_request = ActionRequest(
                action_type=action_type,
                intent=intent,
                params=data,
                reasoning=data.get("reasoning", "")
            )

            # If it's a direct chat or non-executable, return immediately
            if intent in NON_EXECUTABLE_INTENTS:
                return self._create_chat_response(data, ai_output, action_request)

            # If it's a read-only intent, return with action_request
            if intent in READ_ONLY_INTENTS:
                return PlanResponse(
                    reasoning=action_request.reasoning,
                    action_request=action_request,
                    plan=None # Will be handled by ActionRouter
                )
            
            # Confirmation Handler
            if intent in CONFIRMATION_INTENTS:
                return self._handle_confirmation(data, user_input, action_request)
            
            # If it's an executable intent, create a real plan
            if intent in EXECUTABLE_INTENTS:
                return self._create_executable_plan(data, action_request)
            
            # Default fallback for unknown intents
            return self._create_chat_response(data, ai_output, action_request)

        except Exception:
            # Fallback for non-JSON or malformed responses
            return self._create_fallback_response(ai_output)

    def _handle_confirmation(self, data: Dict, user_input: str, action_request: ActionRequest) -> PlanResponse:
        """Handle 'yes' or 'run it' by mapping to a confirmation intent."""
        plan = Plan(
            title="Action Confirmation",
            intent="confirm_previous_action",
            risk_level="low",
            requires_approval=False,
            steps=[PlanStep(description="Confirming previous action...", tool="assistant", requires_approval=False)]
        )
        return PlanResponse(reasoning=action_request.reasoning, plan=plan, action_request=action_request)

    def _create_chat_response(self, data: Dict, raw_text: str, action_request: ActionRequest) -> PlanResponse:
        reasoning = data.get("reasoning", "AI provided a direct response.")
        
        # Priority 1: Direct 'content' field
        content = data.get("content")
        
        # Priority 2: Description of the first step in the plan
        if not content:
            plan_data = data.get("plan", data)
            steps = plan_data.get("steps", [])
            if steps:
                content = steps[0].get("description")
        
        # Priority 3: Fallback to raw text
        if not content:
            if raw_text.strip().startswith("{"):
                 content = "AI response was structured but lacked clear content."
            else:
                 content = raw_text
        
        plan = Plan(
            title="Assistant Response",
            intent=action_request.intent,
            risk_level="low",
            requires_approval=False,
            steps=[PlanStep(description=content, tool="assistant", requires_approval=False)]
        )
        return PlanResponse(reasoning=reasoning, plan=plan, action_request=action_request)

    def _create_executable_plan(self, data: Dict, action_request: ActionRequest) -> PlanResponse:
        plan_data = data.get("plan", data)
        
        # Validate steps
        steps_raw = plan_data.get("steps", [])
        if not steps_raw:
            return self._create_fallback_response(json.dumps(data))
            
        plan = Plan(
            title=plan_data.get("title", "Action Plan"),
            intent=plan_data.get("intent", "pc_task"),
            risk_level=plan_data.get("risk_level", "medium"),
            risk_summary=plan_data.get("risk_summary", "This action modifies system state or runs external tools."),
            requires_approval=True,
            steps=[
                PlanStep(
                    description=s.get("description"),
                    tool=s.get("tool", "shell"),
                    command=s.get("command", ""),
                    requires_approval=s.get("requires_approval", True)
                ) for s in steps_raw[:5]
            ]
        )
        return PlanResponse(reasoning=action_request.reasoning, plan=plan, action_request=action_request)

    def _create_fallback_response(self, raw_text: str) -> PlanResponse:
        return PlanResponse(
            reasoning="AI returned text response.",
            plan=Plan(
                title="Assistant Response",
                intent="chat_only",
                risk_level="low",
                requires_approval=False,
                steps=[PlanStep(description=raw_text, tool="assistant", requires_approval=False)]
            )
        )

    def save_plan(self, plan: Plan) -> int:
        from assistant.db.models import Task, TaskStep
        task = Task(description=plan.title, status="pending")
        self.db.session.add(task)
        self.db.session.commit()
        
        for i, step in enumerate(plan.steps):
            db_step = TaskStep(
                task_id=task.id,
                description=step.description,
                order=i,
                status="pending",
                command=step.command
            )
            self.db.session.add(db_step)
        self.db.session.commit()
        return task.id
