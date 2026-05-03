from pydantic import BaseModel
from typing import List, Optional, Any
from assistant.ai.schemas import ActionRequest

from enum import Enum

from assistant.ai.schemas import (
    IntentCategory, ActionType, TargetClass, 
    PlanStep, Plan
)

NON_EXECUTABLE_INTENTS = {
    IntentCategory.CHAT,
    IntentCategory.TOOL_HELP,
    "coding_help",
    "command_help",
    "concept_explanation",
    "general_question",
    "chat_response"
}

READ_ONLY_INTENTS = {
    IntentCategory.DATE_TIME_LOOKUP,
    IntentCategory.LOCAL_SYSTEM_INFO,
    IntentCategory.LOCAL_IP_LOOKUP,
    IntentCategory.PUBLIC_IP_LOOKUP,
    "tool_list",
    "config_read",
    "history_read",
    "workspace_list",
    "ai_list",
}

SECURITY_INTENTS = {
    IntentCategory.NETWORK_SCAN,
    "network_action",
    "exploit_test",
    "vulnerability_scan",
    "recon",
}

CONFIRMATION_INTENTS = {
    "confirm_previous_action",
}

EXECUTABLE_INTENTS = {
    IntentCategory.NETWORK_SCAN,
    "command_execute",
    "tool_run",
    "file_modify",
    "install_package",
    "delete_action",
}


class PlanResponse(BaseModel):
    reasoning: str
    content_text: Optional[str] = None
    plan: Optional[Plan] = None
    action_request: Optional[ActionRequest] = None
    
    @property
    def content(self) -> str:
        # If we have explicit content_text, use it
        if self.content_text:
            return self.content_text
            
        # If we have a plan with steps, and it's a non-executable or read-only intent, 
        # use the first step's description as the primary content.
        if self.plan and self.plan.steps:

            if self.plan.intent in NON_EXECUTABLE_INTENTS or self.plan.intent in READ_ONLY_INTENTS:
                return self.plan.steps[0].description
        
        # Final Fallback: Generate a useful pre-execution explanation from the plan
        if self.plan:
            steps_desc = ""
            if self.plan.steps:
                steps_desc = f"First step: {self.plan.steps[0].description}."
            
            return f"'{self.plan.title}'. {steps_desc}"
                
        return "I'm not sure how to process this request."


