import json
from typing import List, Dict, Optional, Any
from assistant.db.database import DatabaseManager
from assistant.tasks.task_types import (
    Plan, PlanStep, PlanResponse, 
    NON_EXECUTABLE_INTENTS, EXECUTABLE_INTENTS,
    READ_ONLY_INTENTS, CONFIRMATION_INTENTS
)
from assistant.ai.schemas import ActionRequest

class Planner:
    def __init__(self, db: DatabaseManager, system_info: Optional[Any] = None):
        self.db = db
        self.system_info = system_info

    def create_plan(self, ai_output: str, user_input: str) -> PlanResponse:
        """
        Converts AI output into a PlanResponse using unified schemas.
        """
        from assistant.ai.schemas import validate_ai_response, ActionType
        from assistant.tasks.task_types import READ_ONLY_INTENTS, NON_EXECUTABLE_INTENTS, CONFIRMATION_INTENTS


        # Validate and parse using unified schemas
        validated = validate_ai_response(ai_output)
        res = validated.response

        # Phase 6.4: Defensive flattening of non-standard 'tasks' list
        # If the AI returned a list of tasks instead of a single plan, flatten them.
        try:
            data = json.loads(ai_output)
            if "tasks" in data and isinstance(data["tasks"], list) and not res.plan:
                from assistant.ai.schemas import Plan as SchemaPlan
                all_steps = []
                combined_title = "Combined Tasks"
                for t in data["tasks"]:
                    if "plan" in t and "steps" in t["plan"]:
                        all_steps.extend(t["plan"]["steps"])
                        if "title" in t["plan"] and combined_title == "Combined Tasks":
                            combined_title = t["plan"]["title"]
                
                if all_steps:
                    res.plan = SchemaPlan(
                        title=combined_title,
                        steps=all_steps
                    )
        except:
            pass

        # Create ActionRequest for backward compatibility with executor
        action_request = ActionRequest(
            action_type=res.action_type or ActionType.NO_ACTION,
            intent=res.intent or "unknown",
            target_class=res.target_class or "none",
            params=res.model_dump(),
            reasoning=res.reasoning or "AI provided a technical response."
        )


        # 1. Read-only handlers - DO NOT RETURN EARLY IF PLAN EXISTS
        # We want to execute read-only commands (like 'ls' or 'ip addr')
        if not res.plan:
            if res.action_type in [ActionType.READ_ONLY_LOCAL, ActionType.BENIGN_WEB_LOOKUP] or res.intent in READ_ONLY_INTENTS:
                return PlanResponse(
                    reasoning=res.reasoning,
                    content_text=res.content,
                    action_request=action_request,
                    plan=None
                )


        # 2. Chat / No Action
        if res.action_type == ActionType.NO_ACTION or res.intent in NON_EXECUTABLE_INTENTS:
            return PlanResponse(
                reasoning=res.reasoning,
                content_text=res.content,
                action_request=action_request,
                plan=None
            )


        # 3. Confirmation Handler
        if res.intent in CONFIRMATION_INTENTS:
            return self._handle_confirmation(res.model_dump(), user_input, action_request)

        # 4. Executable actions (or any action with a plan)
        if res.plan:
            return self._create_executable_plan_from_schema(res.plan, action_request)
        
        if res.action_type in [ActionType.SECURITY_SCAN, ActionType.COMMAND_EXECUTION, ActionType.FILE_WRITE, ActionType.DESTRUCTIVE_ACTION]:
            # Fallback if executable but no plan provided in schema (legacy or malformed)
            return self._create_fallback_response(ai_output)


        # Default fallback
        return PlanResponse(
            reasoning=res.reasoning,
            content_text=res.content,
            action_request=action_request,
            plan=None
        )



    def _create_executable_plan_from_schema(self, plan_schema: Any, action_request: ActionRequest) -> PlanResponse:
        """Helper to convert Pydantic Plan schema to Task PlanResponse."""
        plan = Plan(
            title=plan_schema.title,
            intent=plan_schema.intent,
            risk_level=plan_schema.risk_level,
            risk_summary=plan_schema.risk_summary or "Action requires execution.",
            requires_approval=plan_schema.requires_approval,
            steps=[
                PlanStep(
                    description=s.description,
                    tool=s.tool,
                    command=s.command,
                    requires_approval=s.requires_approval
                ) for s in plan_schema.steps[:10]
            ]
        )
        return PlanResponse(reasoning=action_request.reasoning, plan=plan, action_request=action_request)


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

    # _create_chat_response() REMOVED — Phase 4 cleanup.
    # Superseded by _create_executable_plan_from_schema() + PlanResponse.content property.

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
        """Save a plan to the database using the unified manager."""
        return self.db.save_task_plan(plan.title, plan.steps)

