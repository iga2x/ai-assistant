from typing import List, Optional
from pydantic import BaseModel
from assistant.ai.detector import detect_providers, AIProvider
import httpx
import os
from typing import Any

class RuntimeAIState(BaseModel):
    provider: str
    model: Optional[str] = None
    available: bool = False
    models: List[str] = []
    source: str = "none" # config, auto_detected, running_model, fallback, none

class AIRuntime:
    def __init__(self, config: Any):
        self._config_obj = config
        self.state = RuntimeAIState(provider="none", source="none")
        self.providers: List[AIProvider] = []

    @property
    def config(self) -> Any:
        """Helper to get AppConfig whether we were passed ConfigManager or AppConfig."""
        if hasattr(self._config_obj, "config"):
            return self._config_obj.config
        return self._config_obj

    async def refresh(self):
        """Re-scan services and resolve the active model."""
        from assistant.memory import MemoryManager
        memory = MemoryManager()
        secrets = memory.get_all_facts().get("secrets", {})
        self.providers = detect_providers(secrets)
        await self.resolve()

    async def resolve(self):
        """Determine the best active model based on priority rules."""
        # 1. Try Ollama (most common local)
        ollama = next((p for p in self.providers if p.name == "ollama" and p.available), None)
        if ollama:
            await self._resolve_ollama(ollama)
            if self.state.available:
                return

        # 2. Try Cloud if local not found or configured to prioritize cloud
        if self.config.ai.mode == "cloud_only" or (not self.state.available and self.config.ai.mode == "local_first"):
            self._resolve_cloud()

        # 3. Final Fallback if allowed
        if not self.state.available and self.config.ai.allow_mock_fallback:
            self.state = RuntimeAIState(
                provider="mock",
                model="offline-mock",
                available=True,
                source="fallback"
            )

    async def _resolve_ollama(self, provider: AIProvider):
        # Rule: Prefer running model if enabled
        if self.config.ai.prefer_running_model:
            running = await self._get_ollama_running_models(provider.endpoint)
            if running:
                self.state = RuntimeAIState(
                    provider="ollama",
                    model=running[0],
                    available=True,
                    models=provider.models,
                    source="running_model"
                )
                return

        # Rule: Use config default if installed
        config_default = self.config.ai.default_local_model
        if config_default and config_default in provider.models:
            self.state = RuntimeAIState(
                provider="ollama",
                model=config_default,
                available=True,
                models=provider.models,
                source="config"
            )
            return

        # Rule: Auto-select first if enabled
        if self.config.ai.auto_select_model and provider.models:
            self.state = RuntimeAIState(
                provider="ollama",
                model=provider.models[0],
                available=True,
                models=provider.models,
                source="auto_detected"
            )
            return

    def _resolve_cloud(self):
        """Dynamic resolution for cloud providers with fallbacks."""
        # 1. Try to use configured default cloud provider
        config_provider = self.config.ai.default_cloud_provider
        provider = next((p for p in self.providers if p.name == config_provider and p.available), None)
        
        # 2. Fallback to any available cloud provider
        if not provider:
            provider = next((p for p in self.providers if p.type == "cloud" and p.available), None)
            
        if provider:
            # Determine model
            model = self.config.ai.default_cloud_model
            source = "config"
            
            # If auto-select is enabled and config model is missing or not in available models
            if self.config.ai.auto_select_model:
                if not model or (provider.models and model not in provider.models):
                    if provider.models:
                        # Prefer 'coding' or 'pro' or 'large' models if they exist in the names
                        coding_models = [m for m in provider.models if "coding" in m.lower() or "code" in m.lower()]
                        if coding_models:
                            model = coding_models[0]
                        else:
                            model = provider.models[0]
                        source = "auto_detected"
            
            # Emergency fallback if still no model string
            if not model:
                defaults = {
                    "openai": "gpt-4o-mini", 
                    "groq": "llama-3.1-70b-versatile", 
                    "openrouter": "google/gemini-flash-1.5",
                    "zai_coding": "codegeex-4"
                }
                model = defaults.get(provider.name, "default")
                source = "fallback"

            self.state = RuntimeAIState(
                provider=provider.name,
                model=model,
                available=True,
                models=provider.models,
                source=source
            )

    async def _get_ollama_running_models(self, endpoint: str) -> List[str]:
        """Query /api/ps to see what's actually in memory."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{endpoint}/api/ps", timeout=2.0)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return [m["name"] for m in models]
        except Exception:
            pass
        return []

    def get_state(self) -> RuntimeAIState:
        return self.state
