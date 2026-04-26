from assistant.tasks.task_types import (
    NON_EXECUTABLE_INTENTS,
    READ_ONLY_INTENTS,
    EXECUTABLE_INTENTS
)

def requires_approval(action_type: str, intent: str) -> bool:
    """
    Decide if an action requires user approval.
    """
    if action_type == "approval_required_action":
        return True
    
    if action_type == "risky_tool_action" or action_type == "security_scan":
        return True
    
    if intent in EXECUTABLE_INTENTS:
        return True
    
    if intent in READ_ONLY_INTENTS or intent in NON_EXECUTABLE_INTENTS:
        return False
        
    return False # Default to safe for now, can be hardened
