import yaml
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, List
from assistant.utils.paths import CONFIG_FILE

class IdentityConfig(BaseModel):
    name: str = "AI Assistant"
    persona: str = "A professional and efficient technical assistant specializing in system administration and security."
    use_antigravity_branding: bool = False


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
    save_all_outputs: bool = False
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

class NetworkConfig(BaseModel):
    public_ip_providers: List[str] = ["https://api.ipify.org?format=json", "https://ifconfig.me/all.json"]
    reachability_check_ip: str = "1.1.1.1" # Used to find local IP

class DebugConfig(BaseModel):
    show_ai_reasoning: bool = False
    show_raw_ai_response: bool = False
    show_intent: bool = False
    show_plan: bool = False

class TimeoutConfig(BaseModel):
    """Centralized timeout configuration for various operations."""
    default: int = 60  # Default timeout in seconds
    ai_request: int = 90  # AI API request timeout
    shell_command: int = 300  # Shell command execution (5 minutes for long scans)
    web_request: int = 30  # HTTP/web requests
    tool_detection: int = 10  # Tool version detection
    nmap_scan: int = 300  # Nmap scan timeout (long scans)
    # Tool-specific timeouts
    tool: dict = Field(default_factory=lambda: {
        "nmap": 300,
        "nuclei": 180,
        "sqlmap": 300,
        "ffuf": 120,
        "gobuster": 120,
        "hydra": 180,
        "john": 300,
        "hashcat": 300,
    })

class AppConfig(BaseModel):
    identity: IdentityConfig = Field(default_factory=IdentityConfig)
    ai: AIConfig = Field(default_factory=AIConfig)

    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    debug: DebugConfig = Field(default_factory=DebugConfig)
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig)

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
