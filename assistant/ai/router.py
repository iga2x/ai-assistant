import httpx
import json
from typing import List, Dict, Any, Optional
from assistant.ai.detector import detect_providers, AIProvider
from assistant.tasks.task_types import PlanResponse, Plan, PlanStep
from assistant.ai.runtime import AIRuntime, RuntimeAIState

class AIRouter:
    def __init__(self, config: Any):
        self._config_obj = config
        self.runtime = AIRuntime(config)

    @property
    def config(self) -> Any:
        """Helper to get AppConfig whether we were passed ConfigManager or AppConfig."""
        if hasattr(self._config_obj, "config"):
            return self._config_obj.config
        return self._config_obj

    async def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        # Refresh runtime state before chat (Phase 2.7)
        await self.runtime.refresh()
        state = self.runtime.get_state()
        
        if not state.available:
            if self.config.ai.allow_mock_fallback:
                return self.mock_response(messages)
            return json.dumps({
                "reasoning": "No AI model is available and mock fallback is disabled.",
                "intent": "chat_only",
                "content": "No AI model available. Please start Ollama or configure a cloud provider.",
                "plan": {"title": "Error", "intent": "chat_only", "steps": []}
            })

        if state.provider == "ollama":
            try:
                res = await self._ollama_chat(state, messages)
                if res and not any(err in res for err in ["Error connecting", "Failed to get", "Ollama error"]):
                    return res
            except Exception:
                pass
        
        # If real provider failed, return mock as last resort if allowed
        if self.config.ai.allow_mock_fallback:
            return self.mock_response(messages)
            
        return json.dumps({
            "reasoning": f"Primary provider {state.provider} failed and mock fallback is disabled.",
            "intent": "chat_only",
            "content": f"The AI provider ({state.provider}) failed to respond. Please check the service logs.",
            "plan": {"title": "Error", "intent": "chat_only", "steps": []}
        })

    async def _ollama_chat(self, state: RuntimeAIState, messages: List[Dict[str, str]]) -> str:
        # Get endpoint from detector via providers list in runtime
        provider = next((p for p in self.runtime.providers if p.name == "ollama"), None)
        if not provider:
            return "Ollama provider not found in runtime."

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{provider.endpoint}/api/chat",
                    json={
                        "model": state.model, 
                        "messages": messages, 
                        "stream": False, 
                        "options": {"temperature": 0.1},
                        "format": "json"
                    },
                    timeout=90.0
                )
                if response.status_code == 200:
                    content = response.json().get("message", {}).get("content", "")
                    if content:
                        return content
                else:
                    return f"Ollama error {response.status_code}: {response.text}"
        except Exception as e:
            return f"Error connecting to Ollama: {str(e)}"
        return "Failed to get response from Ollama."

    def mock_response(self, messages: List[Dict[str, str]]) -> str:
        """Fallback response for development/offline environments."""
        last_user_msg = messages[-1]["content"].lower()
        
        if "ip" in last_user_msg:
            resp = {
                "reasoning": "The user wants to find their IP. This is a safe system query.",
                "intent": "system_info",
                "plan": {
                    "title": "IP Detection",
                    "intent": "system_info",
                    "steps": [
                        {"description": "Get local IP", "tool": "shell", "command": "hostname -I", "requires_approval": False}
                    ]
                }
            }
            return json.dumps(resp)

        if "scan" in last_user_msg:
            resp = {
                "reasoning": "The user wants to run a network scan. This is an executable action.",
                "intent": "scan",
                "plan": {
                    "title": "Network Scan",
                    "intent": "scan",
                    "risk_level": "medium",
                    "risk_summary": "Runs an active Nmap scan which might be logged.",
                    "steps": [
                        {"description": "Ping localhost", "tool": "shell", "command": "ping -c 1 127.0.0.1", "requires_approval": False},
                        {"description": "Scan localhost", "tool": "shell", "command": "nmap -F 127.0.0.1", "requires_approval": True}
                    ]
                }
            }
            return json.dumps(resp)
        
        resp = {
            "reasoning": "The user is engaging in general conversation.",
            "intent": "chat_only",
            "content": f"I'm in offline mode. You said: {last_user_msg}",
            "plan": {
                "title": "General Response",
                "intent": "chat_only",
                "steps": [
                    {"description": f"I'm in offline mode. You said: {last_user_msg}", "tool": "assistant", "requires_approval": False}
                ]
            }
        }
        return json.dumps(resp)

