import httpx
import os
from typing import List, Dict, Any
from pydantic import BaseModel

class AIProvider(BaseModel):
    name: str
    type: str  # "local" or "cloud"
    available: bool
    models: List[str] = []
    endpoint: str = ""

def check_ollama() -> AIProvider:
    """Check if Ollama is running and get models."""
    endpoint = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        response = httpx.get(f"{endpoint}/api/tags", timeout=5.0)
        if response.status_code == 200:
            models = [m["name"] for m in response.json().get("models", [])]
            return AIProvider(name="ollama", type="local", available=True, models=models, endpoint=endpoint)
    except Exception:
        pass
    return AIProvider(name="ollama", type="local", available=False)

def check_lmstudio() -> AIProvider:
    """Check if LM Studio is running (standard OpenAI-compatible endpoint)."""
    endpoint = os.getenv("LMSTUDIO_HOST", "http://localhost:1234")
    try:
        response = httpx.get(f"{endpoint}/v1/models", timeout=1.0)
        if response.status_code == 200:
            models = [m["id"] for m in response.json().get("data", [])]
            return AIProvider(name="lmstudio", type="local", available=True, models=models, endpoint=endpoint)
    except Exception:
        pass
    return AIProvider(name="lmstudio", type="local", available=False)

def check_openai() -> AIProvider:
    """Check if OpenAI API key is present."""
    key = os.getenv("OPENAI_API_KEY")
    return AIProvider(name="openai", type="cloud", available=bool(key))

def check_anthropic() -> AIProvider:
    """Check if Anthropic API key is present."""
    key = os.getenv("ANTHROPIC_API_KEY")
    return AIProvider(name="anthropic", type="cloud", available=bool(key))

def check_gemini() -> AIProvider:
    """Check if Gemini API key is present."""
    key = os.getenv("GOOGLE_API_KEY")
    return AIProvider(name="gemini", type="cloud", available=bool(key))

def detect_providers() -> List[AIProvider]:
    """Detect all available AI providers."""
    return [
        check_ollama(),
        check_lmstudio(),
        check_openai(),
        check_anthropic(),
        check_gemini()
    ]
