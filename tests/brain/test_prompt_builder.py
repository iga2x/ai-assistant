# tests/brain/test_prompt_builder.py
from assistant.brain.prompt_builder import PromptBuilder
from assistant.system.discovery import SystemInfo
from assistant.config.manager import AppConfig

def test_prompt_builder_includes_structured_response_format():
    # Create minimal SystemInfo and AppConfig for testing
    system_info = SystemInfo(
        os_name="Linux",
        os_detailed="Kali GNU/Linux Rolling",
        architecture="x86_64",
        hostname="test-host",
        username="test-user",
        is_admin=True,
        python_version="3.13.12",
        cpu_count=8,
        total_ram_gb=16.0,
        disk_free_gb=100.0,
        shell="zsh",
        shell_path="/usr/bin/zsh",
        terminal="xterm-256color",
        local_ip="192.168.1.1",
        interfaces=[],
        network_neighbors=[]
    )

    config = AppConfig()

    builder = PromptBuilder(system_info=system_info, config=config)
    prompt = builder.build_system_prompt({}, {}, "chat")
    assert "Answer:" in prompt
    assert "Command / Example:" in prompt
    assert "Details:" in prompt
    assert "Next step:" in prompt
    assert "structured" in prompt.lower()
