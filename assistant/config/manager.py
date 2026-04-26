import yaml
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, List
from assistant.utils.paths import CONFIG_FILE

class AIConfig(BaseModel):
    mode: str = "local_first"
    ask_before_cloud: bool = True
    default_local_provider: str = "ollama"
    default_local_model: Optional[str] = "qwen3.5:9b"
    default_cloud_provider: str = "openai"
    default_cloud_model: Optional[str] = "gpt-4o-mini"
    auto_select_model: bool = True
    prefer_running_model: bool = True
    allow_mock_fallback: bool = False

class ExecutionConfig(BaseModel):
    mode: str = "active" # active, learning
    show_raw_output: bool = False
    save_all_outputs: bool = True
    require_approval_for_security_tools: bool = True

class SecurityConfig(BaseModel):
    block_unknown_targets: bool = True
    require_scope_for_scanning: bool = True
    full_auto_security_tasks: bool = False
    allow_passive_recon_after_approval: bool = True

class ToolsConfig(BaseModel):
    auto_detect: bool = True
    auto_enable_safe_tools: bool = False
    explain_tools_to_beginner: bool = True

class MemoryConfig(BaseModel):
    session_memory: bool = True
    workspace_memory: bool = True
    long_term_memory_requires_approval: bool = True

class PrivacyConfig(BaseModel):
    never_send_to_cloud: List[str] = [
        "api_keys", "passwords", "cookies", "tokens", "private_reports", "client_data"
    ]

class AppConfig(BaseModel):
    ai: AIConfig = Field(default_factory=AIConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)

class ConfigManager:
    def __init__(self, config_path: Path = CONFIG_FILE):
        self.config_path = config_path
        self.config: AppConfig = self.load_config()

    def load_config(self) -> AppConfig:
        if not self.config_path.exists():
            return AppConfig()
        
        try:
            with open(self.config_path, "r") as f:
                data = yaml.safe_load(f)
                if data is None:
                    return AppConfig()
                return AppConfig(**data)
        except Exception:
            # Fallback to default if loading fails
            return AppConfig()

    def save_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            yaml.dump(self.config.model_dump(), f, default_flow_style=False)

    def reset_config(self):
        self.config = AppConfig()
        self.save_config()
