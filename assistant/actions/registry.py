from assistant.actions.handlers import (
    get_current_datetime,
    get_local_ip,
    get_system_summary,
    list_tools,
    list_ai_models
)

ACTION_REGISTRY = {
    "date_time": get_current_datetime,
    "local_ip": get_local_ip,
    "system_info": get_system_summary,
    "tool_list": list_tools,
    "ai_list": list_ai_models,
}

def get_handler(intent: str):
    return ACTION_REGISTRY.get(intent)
