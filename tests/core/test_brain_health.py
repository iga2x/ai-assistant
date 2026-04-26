from assistant.ai.detector import detect_providers
from assistant.brain.prompt_builder import PromptBuilder
from assistant.system.discovery import discover_system

def test_ai_detection():
    providers = detect_providers()
    assert len(providers) > 0

def test_prompt_builder():
    sys_info = discover_system()
    # Mock config for prompt builder
    from assistant.config.manager import AppConfig
    config = AppConfig()
    builder = PromptBuilder(sys_info, config)
    prompt = builder.build_system_prompt({}, "Hello")
    assert "OS:" in prompt
    assert "Hello" not in prompt # System prompt shouldn't contain the user message usually
    assert "Assistant" in prompt
