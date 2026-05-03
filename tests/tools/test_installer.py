"""Test ecosystem installers."""

import pytest
from unittest.mock import patch, Mock
from assistant.tools.installer import (
    install_tool, install_apt, install_go, install_pip, install_cargo,
    update_tool, install_binary, show_manual_instructions
)
from assistant.tools.models import ErrorCode


def test_install_tool_dry_run():
    """Test dry run installation."""
    tool = {
        "name": "nmap",
        "ecosystem": "apt",
        "install_cmd": "apt install nmap"
    }

    result = install_tool(tool, dry_run=True)

    assert result.success is True
    assert "Dry run" in result.message
    assert "apt" in result.message


def test_install_tool_unsupported_ecosystem():
    """Test installation with unsupported ecosystem."""
    tool = {
        "name": "test",
        "ecosystem": "unsupported",
        "install_cmd": "echo test"
    }

    result = install_tool(tool, dry_run=False)

    assert result.success is False
    assert result.code == ErrorCode.NOT_FOUND
    assert "Unsupported ecosystem" in result.message


def test_install_binary_returns_manual():
    """Test binary installation returns manual instructions."""
    tool = {
        "name": "custom_tool",
        "ecosystem": "binary",
        "install_cmd": "cp /path/to/tool /usr/local/bin/"
    }

    result = install_binary(tool)

    assert result.success is False
    assert result.code == ErrorCode.NOT_FOUND
    assert "not yet automated" in result.message


def test_show_manual_instructions():
    """Test manual instruction display."""
    tool = {
        "name": "metasploit",
        "ecosystem": "manual-note",
        "install_cmd": "curl https://...",
        "docs_url": "https://docs.example.com"
    }

    result = show_manual_instructions(tool)

    assert result.success is True
    assert "Manual instructions" in result.message


def test_update_tool_dry_run():
    """Test dry run update."""
    tool = {
        "name": "nmap",
        "ecosystem": "apt",
        "install_cmd": "apt install nmap"
    }

    result = update_tool(tool, dry_run=True)

    assert result.success is True
    assert "Dry run" in result.message


def test_update_tool_unsupported_ecosystem():
    """Test update with unsupported ecosystem."""
    tool = {
        "name": "test",
        "ecosystem": "binary",
        "install_cmd": "echo test"
    }

    result = update_tool(tool, dry_run=False)

    assert result.success is False
    assert result.code == ErrorCode.NOT_FOUND
    assert "Update not supported" in result.message
