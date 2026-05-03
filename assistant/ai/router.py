import httpx
import json
from typing import List, Dict, Any, Optional
from assistant.ai.detector import detect_providers, AIProvider
from assistant.tasks.task_types import PlanResponse, Plan, PlanStep
from assistant.ai.runtime import AIRuntime, RuntimeAIState
from assistant.ai.schemas import ValidatedResponse, create_mock_response

class AIRouter:
    def __init__(self, config: Any):
        self._config_obj = config
        self.runtime = AIRuntime(config)

    async def classify_intent(self, user_input: str) -> dict:
        """Determines if the input is a general 'chat' or a technical 'task' using structured AI interpretation.
        NOTE: Not called from the main pipeline (superseded by single-LLM orchestrator path).
        Retained for potential future use or tooling.
        """
        prompt = f"""Analyze the user's input and determine their intent.
Is the user asking a question, asking for an explanation, or requesting a task execution?

Input: "{user_input}"

Return a JSON object with this exact structure:
{{
  "interaction_type": "chat" | "task" | "unclear",
  "wants_execution": true | false,
  "goal": "description of user's goal",
  "user_facing_response": "your conversational response, answer, or explanation"
}}

Rules:
- If the user asks "how to", "explain", or asks a question, interaction_type is "chat" and wants_execution is false. Answer their question fully in user_facing_response.
- If the user commands you to actively perform an action (e.g. "find my ip", "scan localhost"), interaction_type is "task" and wants_execution is true.
- If unclear, ask for clarification in user_facing_response.
"""
        try:
            res = await self.chat_completion([{"role": "user", "content": prompt}], json_mode=True)
            data = json.loads(res)
            return data
        except Exception as e:
            from assistant.utils.logger import get_logger
            logger = get_logger("ai.router")
            logger.error(f"Intent classification failed: {e}")
            return {"interaction_type": "task", "wants_execution": True, "goal": "Fallback to task", "user_facing_response": ""}




    @property
    def config(self) -> Any:

        """Helper to get AppConfig whether we were passed ConfigManager or AppConfig."""
        if hasattr(self._config_obj, "config"):
            return self._config_obj.config
        return self._config_obj

    async def chat_completion(self, messages: List[Dict[str, str]], json_mode: bool = True) -> str:

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

        # Dispatch by provider
        res = None
        if state.provider == "ollama":
            try:
                res = await self._ollama_chat(state, messages, json_mode)
            except Exception:
                pass
        elif state.provider in ["openai", "openrouter", "groq", "deepseek", "mistral", "lmstudio", "zai", "zai_coding"]:
            try:
                res = await self._openai_compatible_chat(state, messages, json_mode)
            except Exception:
                pass

        
        if res and not any(err in str(res) for err in ["Error connecting", "Failed to get", "error"]):
            return res
        
        # If real provider failed, return mock as last resort if allowed
        if self.config.ai.allow_mock_fallback:
            return self.mock_response(messages)
            
        return json.dumps({
            "reasoning": f"Primary provider {state.provider} failed and mock fallback is disabled.",
            "intent": "chat_only",
            "content": f"The AI provider ({state.provider}) failed to respond. Please check the service logs.",
            "plan": {"title": "Error", "intent": "chat_only", "steps": []}
        })

    async def _ollama_chat(self, state: RuntimeAIState, messages: List[Dict[str, str]], json_mode: bool = True) -> str:

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
                        "format": "json" if json_mode else ""
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

    async def _openai_compatible_chat(self, state: RuntimeAIState, messages: List[Dict[str, str]], json_mode: bool = True) -> str:

        import os
        from assistant.memory import MemoryManager
        memory = MemoryManager()
        stored_secrets = memory.get_all_facts().get("secrets", {})
        
        endpoints = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "openrouter": "https://openrouter.ai/api/v1/chat/completions",
            "groq": "https://api.groq.com/openai/v1/chat/completions",
            "deepseek": "https://api.deepseek.com/chat/completions",
            "mistral": "https://api.mistral.ai/v1/chat/completions",
            "zai": "https://api.z.ai/api/paas/v4/chat/completions",
            "zai_coding": "https://api.z.ai/api/coding/paas/v4/chat/completions",
            "lmstudio": os.getenv("LMSTUDIO_HOST", "http://localhost:1234") + "/v1/chat/completions"
        }
        
        api_keys = {
            "openai": os.getenv("OPENAI_API_KEY") or stored_secrets.get("OPENAI_API_KEY"),
            "openrouter": os.getenv("OPENROUTER_API_KEY") or stored_secrets.get("OPENROUTER_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY") or stored_secrets.get("GROQ_API_KEY"),
            "deepseek": os.getenv("DEEPSEEK_API_KEY") or stored_secrets.get("DEEPSEEK_API_KEY"),
            "mistral": os.getenv("MISTRAL_API_KEY") or stored_secrets.get("MISTRAL_API_KEY"),
            "zai": os.getenv("ZAI_API_KEY") or stored_secrets.get("ZAI_API_KEY"),
            "zai_coding": os.getenv("ZAI_API_KEY") or stored_secrets.get("ZAI_API_KEY"),
            "lmstudio": "not-needed"
        }
        
        url = endpoints.get(state.provider)
        api_key = api_keys.get(state.provider)
        
        if not url:
            return f"No endpoint configured for provider {state.provider}"
        if not api_key and state.provider != "lmstudio":
            return f"No API key found for provider {state.provider}"
            
        headers = {
            "Content-Type": "application/json",
        }
        if api_key and api_key != "not-needed":
            headers["Authorization"] = f"Bearer {api_key}"
        
        # OpenRouter specific headers
        if state.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/iganomono/ai-assistant"
            headers["X-Title"] = "AI Assistant"

        payload = {
            "model": state.model,
            "messages": messages,
            "temperature": 0.1
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}


        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=60.0)
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return content
                else:
                    return f"API error {response.status_code}: {response.text}"
        except Exception as e:
            return f"Error connecting to {state.provider}: {str(e)}"

    def mock_response(self, messages: List[Dict[str, str]]) -> str:
        """Fallback response for development/offline environments using schema."""
        last_user_msg = messages[-1]["content"]

        # Use the new schema-based mock response system
        validated = create_mock_response(last_user_msg)

        # Convert back to JSON for compatibility with existing code
        if validated.response.plan:
            return json.dumps({
                "reasoning": validated.response.reasoning,
                "intent": validated.response.intent,
                "action_type": validated.response.action_type,
                "plan": {
                    "title": validated.response.plan.title,
                    "intent": validated.response.plan.intent,
                    "risk_level": validated.response.plan.risk_level,
                    "risk_summary": validated.response.plan.risk_summary,
                    "steps": [
                        {
                            "description": step.description,
                            "tool": step.tool,
                            "command": step.command,
                            "requires_approval": step.requires_approval
                        }
                        for step in validated.response.plan.steps
                    ]
                }
            })
        else:
            return json.dumps({
                "reasoning": validated.response.reasoning,
                "intent": validated.response.intent,
                "content": validated.response.content
            })

