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

    @property
    def is_available(self) -> bool:
        return self.available

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

def check_openai(secrets: Dict[str, str] = None) -> AIProvider:
    """Check if OpenAI API key is present and fetch models."""
    secrets = secrets or {}
    key = os.getenv("OPENAI_API_KEY") or secrets.get("OPENAI_API_KEY")
    if not key:
        return AIProvider(name="openai", type="cloud", available=False)
    
    models = []
    is_available = False
    try:
        headers = {"Authorization": f"Bearer {key}"}
        response = httpx.get("https://api.openai.com/v1/models", headers=headers, timeout=2.0)
        if response.status_code == 200:
            models = [m["id"] for m in response.json().get("data", []) if "gpt" in m["id"]]
            is_available = True
    except Exception:
        pass
    return AIProvider(name="openai", type="cloud", available=is_available, models=models)

def check_anthropic(secrets: Dict[str, str] = None) -> AIProvider:
    """Check if Anthropic API key is present."""
    secrets = secrets or {}
    key = os.getenv("ANTHROPIC_API_KEY") or secrets.get("ANTHROPIC_API_KEY")
    return AIProvider(name="anthropic", type="cloud", available=bool(key))

def check_gemini(secrets: Dict[str, str] = None) -> AIProvider:
    """Check if Gemini API key is present."""
    secrets = secrets or {}
    key = os.getenv("GOOGLE_API_KEY") or secrets.get("GOOGLE_API_KEY")
    return AIProvider(name="gemini", type="cloud", available=bool(key))

def check_openrouter(secrets: Dict[str, str] = None) -> AIProvider:
    """Check if OpenRouter API key is present and fetch models."""
    secrets = secrets or {}
    key = os.getenv("OPENROUTER_API_KEY") or secrets.get("OPENROUTER_API_KEY")
    if not key:
        return AIProvider(name="openrouter", type="cloud", available=False)
    
    models = []
    is_available = False
    try:
        headers = {"Authorization": f"Bearer {key}"}
        response = httpx.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=2.0)
        if response.status_code == 200:
            models = [m["id"] for m in response.json().get("data", [])]
            is_available = True
    except Exception:
        pass
    return AIProvider(name="openrouter", type="cloud", available=is_available, models=models)

def check_groq(secrets: Dict[str, str] = None) -> AIProvider:
    """Check if Groq API key is present and fetch models."""
    secrets = secrets or {}
    key = os.getenv("GROQ_API_KEY") or secrets.get("GROQ_API_KEY")
    if not key:
        return AIProvider(name="groq", type="cloud", available=False)
    
    models = []
    is_available = False
    try:
        headers = {"Authorization": f"Bearer {key}"}
        response = httpx.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=2.0)
        if response.status_code == 200:
            models = [m["id"] for m in response.json().get("data", [])]
            is_available = True
    except Exception:
        pass
    return AIProvider(name="groq", type="cloud", available=is_available, models=models)

def check_deepseek(secrets: Dict[str, str] = None) -> AIProvider:
    """Check if DeepSeek API key is present and fetch models."""
    secrets = secrets or {}
    key = os.getenv("DEEPSEEK_API_KEY") or secrets.get("DEEPSEEK_API_KEY")
    if not key:
        return AIProvider(name="deepseek", type="cloud", available=False)
    
    models = []
    is_available = False
    try:
        headers = {"Authorization": f"Bearer {key}"}
        response = httpx.get("https://api.deepseek.com/models", headers=headers, timeout=2.0)
        if response.status_code == 200:
            models = [m["id"] for m in response.json().get("data", [])]
            is_available = True
    except Exception:
        pass
    return AIProvider(name="deepseek", type="cloud", available=is_available, models=models)

def check_mistral(secrets: Dict[str, str] = None) -> AIProvider:
    """Check if Mistral API key is present and fetch models."""
    secrets = secrets or {}
    key = os.getenv("MISTRAL_API_KEY") or secrets.get("MISTRAL_API_KEY")
    if not key:
        return AIProvider(name="mistral", type="cloud", available=False)
    
    models = []
    is_available = False
    try:
        headers = {"Authorization": f"Bearer {key}"}
        response = httpx.get("https://api.mistral.ai/v1/models", headers=headers, timeout=2.0)
        if response.status_code == 200:
            models = [m["id"] for m in response.json().get("data", [])]
            is_available = True
    except Exception:
        pass
    return AIProvider(name="mistral", type="cloud", available=is_available, models=models)

def check_zai(secrets: Dict[str, str] = None) -> AIProvider:
    """Check if Z.AI API key is present and fetch models."""
    secrets = secrets or {}
    key = os.getenv("ZAI_API_KEY") or secrets.get("ZAI_API_KEY")
    if not key:
        return AIProvider(name="zai", type="cloud", available=False)
    
    models = []
    is_available = False
    try:
        headers = {"Authorization": f"Bearer {key}"}
        response = httpx.get("https://api.z.ai/api/paas/v4/models", headers=headers, timeout=2.0)
        if response.status_code == 200:
            models = [m["id"] for m in response.json().get("data", [])]
            is_available = True
    except Exception:
        pass
    return AIProvider(name="zai", type="cloud", available=is_available, models=models)

def check_zai_coding(secrets: Dict[str, str] = None) -> AIProvider:
    """Check if Z.AI API key is present and fetch models."""
    secrets = secrets or {}
    key = os.getenv("ZAI_API_KEY") or secrets.get("ZAI_API_KEY")
    if not key:
        return AIProvider(name="zai_coding", type="cloud", available=False)
    
    models = []
    is_available = False
    try:
        headers = {"Authorization": f"Bearer {key}"}
        response = httpx.get("https://api.z.ai/api/coding/paas/v4/models", headers=headers, timeout=2.0)
        if response.status_code == 200:
            models = [m["id"] for m in response.json().get("data", [])]
            is_available = True
    except Exception:
        pass
    return AIProvider(name="zai_coding", type="cloud", available=is_available, models=models)

def detect_providers(secrets: Dict[str, str] = None) -> List[AIProvider]:
    """Detect all available AI providers."""
    return [
        check_ollama(),
        check_lmstudio(),
        check_openai(secrets),
        check_anthropic(secrets),
        check_gemini(secrets),
        check_openrouter(secrets),
        check_groq(secrets),
        check_deepseek(secrets),
        check_mistral(secrets),
        check_zai(secrets),
        check_zai_coding(secrets)
    ]
