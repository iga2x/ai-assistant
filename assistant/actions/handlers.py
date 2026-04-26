from datetime import datetime
from typing import Dict, Any
from assistant.actions.schemas import ActionResult

def get_current_datetime(params: Dict[str, Any], context: Any) -> ActionResult:
    now = datetime.now()
    formatted = now.strftime("%A, %B %d, %Y %I:%M %p")
    return ActionResult(
        success=True,
        output=f"Today is [bold cyan]{formatted}[/bold cyan]",
        data={"datetime": now.isoformat()},
        action_type="read_only_system_action",
        intent="date_time"
    )

def get_local_ip(params: Dict[str, Any], context: Any) -> ActionResult:
    sys_info = context.get("sys_info")
    ip = sys_info.local_ip if sys_info else "unknown"
    return ActionResult(
        success=True,
        output=f"Your local IP address is: [bold cyan]{ip}[/bold cyan]",
        data={"ip": ip},
        action_type="read_only_system_action",
        intent="local_ip"
    )

def get_system_summary(params: Dict[str, Any], context: Any) -> ActionResult:
    sys_info = context.get("sys_info")
    if sys_info:
        output = f"System: [bold cyan]{sys_info.os_detailed}[/bold cyan] | Host: [bold cyan]{sys_info.hostname}[/bold cyan]"
        data = {"os": sys_info.os_detailed, "hostname": sys_info.hostname}
    else:
        output = "System info currently unavailable."
        data = {}
    
    return ActionResult(
        success=True,
        output=output,
        data=data,
        action_type="read_only_system_action",
        intent="system_info"
    )

def list_tools(params: Dict[str, Any], context: Any) -> ActionResult:
    # This would ideally call the tool discovery service
    return ActionResult(
        success=True,
        output="I have access to tools like nmap, git, nuclei, and more. Use `/status` to see the full list.",
        action_type="read_only_system_action",
        intent="tool_list"
    )

def list_ai_models(params: Dict[str, Any], context: Any) -> ActionResult:
    return ActionResult(
        success=True,
        output="I am currently running on the selected AI model. Use `assistant ai list` for details.",
        action_type="read_only_system_action",
        intent="ai_list"
    )
