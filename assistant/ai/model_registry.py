from typing import Dict, Any, List
from pydantic import BaseModel

class ModelInfo(BaseModel):
    name: str
    description: str
    parameters: str
    quantization: str
    capabilities: List[str] = []

# This registry can be expanded with specific model capabilities or recommended prompts
RECOMMENDED_MODELS = {
    "qwen3.5:9b": ModelInfo(
        name="qwen3.5:9b",
        description="High-performance 9B model optimized for code and reasoning.",
        parameters="9.7B",
        quantization="Q4_K_M",
        capabilities=["coding", "reasoning", "json_format"]
    ),
    "llama3.1:8b": ModelInfo(
        name="llama3.1:8b",
        description="Meta's versatile 8B model.",
        parameters="8.0B",
        quantization="Q4_K_M",
        capabilities=["general", "chat"]
    )
}

class ModelRegistry:
    def __init__(self):
        self.models: Dict[str, ModelInfo] = RECOMMENDED_MODELS

    def get_info(self, model_name: str) -> ModelInfo:
        # Normalize name (remove tag if latest)
        name = model_name.split(":")[0] if ":" in model_name and model_name.endswith(":latest") else model_name
        return self.models.get(name) or ModelInfo(
            name=model_name,
            description="Detected local/cloud model.",
            parameters="Unknown",
            quantization="Unknown"
        )
