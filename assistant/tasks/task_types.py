from pydantic import BaseModel
from typing import List, Optional, Any
from assistant.actions.schemas import ActionRequest

NON_EXECUTABLE_INTENTS = {
    "chat_only",
    "tool_help",
    "coding_help",
    "command_help",
    "concept_explanation",
    "general_question",
}

READ_ONLY_INTENTS = {
    "date_time",
    "system_info",
    "local_ip",
    "tool_list",
    "config_read",
    "history_read",
    "workspace_list",
    "ai_list",
}

CONFIRMATION_INTENTS = {
    "confirm_previous_action",
}

EXECUTABLE_INTENTS = {
    "scan",
    "command_execute",
    "tool_run",
    "file_modify",
    "install_package",
    "delete_action",
    "network_action",
}

class PlanStep(BaseModel):
    description: str
    tool: str = "shell"
    command: str = ""
    requires_approval: bool = True
    status: str = "pending"
    order: int = 0

class Plan(BaseModel):
    title: str
    intent: str
    risk_level: str = "low"  # low, medium, high, critical
    risk_summary: str = ""
    requires_approval: bool = False
    steps: List[PlanStep]

class PlanResponse(BaseModel):
    reasoning: str
    plan: Optional[Plan] = None
    action_request: Optional[ActionRequest] = None
    
    @property
    def content(self) -> str:
        # If we have a plan with steps, and it's a non-executable or read-only intent, 
        # use the first step's description as the primary content.
        if self.plan and self.plan.steps:
            if self.plan.intent in NON_EXECUTABLE_INTENTS or self.plan.intent in READ_ONLY_INTENTS:
                return self.plan.steps[0].description
        
        # Fallback to reasoning if no plan steps or if it's an executable plan that hasn't run yet
        return self.reasoning

