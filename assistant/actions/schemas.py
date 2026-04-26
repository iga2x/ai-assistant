from pydantic import BaseModel
from typing import Optional, Any, Dict, List

class ActionRequest(BaseModel):
    action_type: str  # chat_response, read_only_system_action, safe_local_command, risky_tool_action, etc.
    intent: str
    params: Dict[str, Any] = {}
    reasoning: str = ""

class ActionResult(BaseModel):
    success: bool
    output: str
    data: Optional[Any] = None
    error: Optional[str] = None
    action_type: str
    intent: str
