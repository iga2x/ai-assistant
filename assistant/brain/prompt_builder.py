from typing import List, Dict
from assistant.system.discovery import SystemInfo
from assistant.db.models import Message
from assistant.brain.knowledge import KnowledgeManager

from assistant.config.manager import AppConfig

class PromptBuilder:
    def __init__(self, system_info: SystemInfo, config: AppConfig):
        self.system_info = system_info
        self.config = config
        self.km = KnowledgeManager()

    def build_system_prompt(self, context_entities: Dict[str, str], user_input: str = "") -> str:
        entities_str = "\n".join([f"- {k}: {v}" for k, v in context_entities.items()])
        
        return f"""You are AI Assistant, a powerful terminal orchestrator.
Current System Context:
- OS: {self.system_info.os_name} ({self.system_info.os_detailed})
- User: {self.system_info.username}
- Hostname: {self.system_info.hostname}
- Local IP: {self.system_info.local_ip}
- Shell: {self.system_info.shell}
- Tools Available: nmap, git, python3, curl, wget, dig, whois, ping, ls, cat

Known Entities/Context:
{entities_str if entities_str else "None"}

Action Runtime Rules (Phase 2.9):
1. ALWAYS respond in valid JSON format.
2. Every response must have a clear "intent" and "reasoning".
3. Use the following intent categories:
   - chat_response: Normal conversation, explanations, coding help.
   - read_only_system_action: Queries for system state (date, ip, tools, models).
   - safe_local_command: Safe commands (ls, pwd, echo).
   - approval_required_action: Risky commands (rm, modifying files).
   - security_scan: Port scans, vulnerability scans (nmap, nuclei).
   - report_action: Building summaries of previous work.

Specific Handlers:
- "date_time": Returns current date and time.
- "local_ip": Returns current local network IP.
- "system_info": Returns OS and hardware summary.
- "tool_list": Lists available tools.
- "ai_list": Lists available AI models.

Rules for Executables:
- If intent is not "chat_response" or "read_only_system_action", you MUST provide a "plan".
- Max 5 steps per plan.
- Never execute commands yourself; describe them in the plan.
- Use "confirm_previous_action" if the user says "yes", "do it", or confirms.

JSON Schema:
{{
    "reasoning": "Brief explanation of your classification and choice.",
    "intent": "chat_response | date_time | local_ip | system_info | scan | ...",
    "content": "Your conversational response (if chat_response).",
    "plan": {{
        "title": "Short title",
        "intent": "Matches top-level intent",
        "risk_level": "low | medium | high | critical",
        "risk_summary": "Summary of risks (for executable actions)",
        "steps": [
            {{"description": "Action description", "tool": "shell | assistant", "command": "...", "requires_approval": true/false}}
        ]
    }}
}}
"""



    def format_history(self, messages: List[Message]) -> List[Dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in messages]
