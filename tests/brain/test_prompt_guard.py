"""
Test for Task 1: Prompt-level guard for system context usage

This test verifies that the system prompt contains proper guards to prevent
the AI from leaking system context information inappropriately.

TDD Process:
1. Write test first (RED state - test should fail)
2. Run test to confirm it fails
3. Verify implementation exists (test should pass - GREEN state)
4. Clean up temporary test file
5. Commit test to proper location
"""

import pytest
from assistant.system.discovery import SystemInfo
from assistant.config.manager import AppConfig
from assistant.brain.prompt_builder import PromptBuilder


def create_test_system_info() -> SystemInfo:
    """Create a mock SystemInfo object for testing."""
    return SystemInfo(
        os_name="Linux",
        os_detailed="Linux 6.18.12+kali-amd64",
        architecture="x86_64",
        hostname="test-host",
        username="testuser",
        is_admin=True,
        python_version="3.13.12",
        cpu_count=8,
        total_ram_gb=16.0,
        disk_free_gb=50.0,
        shell="zsh",
        shell_path="/usr/bin/zsh",
        terminal="xterm-256color",
        local_ip="192.168.1.100",
        interfaces=["eth0", "lo"],
        network_neighbors=[]
    )


def test_system_prompt_contains_context_usage_rules():
    """Verify that the system prompt contains context usage rules."""
    # Arrange
    system_info = create_test_system_info()
    config = AppConfig()
    prompt_builder = PromptBuilder(system_info, config)

    # Act
    system_prompt = prompt_builder.build_system_prompt(
        context_entities={},
        long_term_memory=None,
        user_input="",
        minimal=False
    )

    # Assert
    assert "SYSTEM CONTEXT USAGE RULES:" in system_prompt, \
        "System prompt must contain 'SYSTEM CONTEXT USAGE RULES:' section"


def test_system_prompt_contains_do_not_mention_warning():
    """Verify that the system prompt contains the 'Do NOT mention' warning."""
    # Arrange
    system_info = create_test_system_info()
    config = AppConfig()
    prompt_builder = PromptBuilder(system_info, config)

    # Act
    system_prompt = prompt_builder.build_system_prompt(
        context_entities={},
        long_term_memory=None,
        user_input="",
        minimal=False
    )

    # Assert
    assert "Do NOT mention system details in your final answer unless:" in system_prompt, \
        "System prompt must contain 'Do NOT mention system details in your final answer unless:' warning"


def test_system_prompt_contains_output_cleanliness_section():
    """Verify that the system prompt contains output cleanliness rules."""
    # Arrange
    system_info = create_test_system_info()
    config = AppConfig()
    prompt_builder = PromptBuilder(system_info, config)

    # Act
    system_prompt = prompt_builder.build_system_prompt(
        context_entities={},
        long_term_memory=None,
        user_input="",
        minimal=False
    )

    # Assert
    assert "OUTPUT CLEANLINESS:" in system_prompt, \
        "System prompt must contain 'OUTPUT CLEANLINESS:' section"


def test_system_prompt_internal_planning_context():
    """Verify that the system prompt specifies context is for internal planning only."""
    # Arrange
    system_info = create_test_system_info()
    config = AppConfig()
    prompt_builder = PromptBuilder(system_info, config)

    # Act
    system_prompt = prompt_builder.build_system_prompt(
        context_entities={},
        long_term_memory=None,
        user_input="",
        minimal=False
    )

    # Assert
    assert "System context (hostname, OS, user, IP, interfaces, installed tools, environment details) is for INTERNAL PLANNING only" in system_prompt, \
        "System prompt must specify that context is for internal planning only"


def test_system_prompt_conditional_exception_list():
    """Verify that the system prompt lists valid exceptions for mentioning system details."""
    # Arrange
    system_info = create_test_system_info()
    config = AppConfig()
    prompt_builder = PromptBuilder(system_info, config)

    # Act
    system_prompt = prompt_builder.build_system_prompt(
        context_entities={},
        long_term_memory=None,
        user_input="",
        minimal=False
    )

    # Assert
    # Check that the exceptions are listed with bullet points
    assert "* The user explicitly asks for:" in system_prompt, \
        "System prompt must include exception for explicit user requests"
    assert "* You are summarizing ACTUAL command execution results that include these details" in system_prompt, \
        "System prompt must include exception for summarizing command results"
    assert "* The detail is required to avoid giving wrong instructions for the user's environment" in system_prompt, \
        "System prompt must include exception for environment-specific instructions"


def test_system_prompt_no_auto_sections():
    """Verify that the system prompt warns against automatically adding system info sections."""
    # Arrange
    system_info = create_test_system_info()
    config = AppConfig()
    prompt_builder = PromptBuilder(system_info, config)

    # Act
    system_prompt = prompt_builder.build_system_prompt(
        context_entities={},
        long_term_memory=None,
        user_input="",
        minimal=False
    )

    # Assert
    assert "Do NOT add sections like \"Your current system info:\" or \"Your hostname:\" to your responses" in system_prompt, \
        "System prompt must warn against adding automatic system info sections"
    assert "Do NOT start responses with \"On [hostname] you're running...\" unless summarizing executed command results" in system_prompt, \
        "System prompt must warn against starting responses with system info"


def test_system_prompt_clean_user_focused_output():
    """Verify that the system prompt emphasizes clean, user-focused output."""
    # Arrange
    system_info = create_test_system_info()
    config = AppConfig()
    prompt_builder = PromptBuilder(system_info, config)

    # Act
    system_prompt = prompt_builder.build_system_prompt(
        context_entities={},
        long_term_memory=None,
        user_input="",
        minimal=False
    )

    # Assert
    assert "Your final answer should be clean, direct, and user-focused" in system_prompt, \
        "System prompt must emphasize clean, user-focused output"
    assert "Do not include planner text, internal reasoning, or workflow names in user-facing content" in system_prompt, \
        "System prompt must warn against including internal text in user-facing content"


def test_minimal_prompt_lacks_context_rules():
    """Verify that minimal mode does NOT include context usage rules (as expected)."""
    # Arrange
    system_info = create_test_system_info()
    config = AppConfig()
    prompt_builder = PromptBuilder(system_info, config)

    # Act
    system_prompt = prompt_builder.build_system_prompt(
        context_entities={},
        long_term_memory=None,
        user_input="",
        minimal=True
    )

    # Assert
    assert "SYSTEM CONTEXT USAGE RULES:" not in system_prompt, \
        "Minimal mode should NOT include system context usage rules"
    assert "OUTPUT CLEANLINESS:" not in system_prompt, \
        "Minimal mode should NOT include output cleanliness rules"
