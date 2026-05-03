"""Ecosystem-specific installers and updaters."""

import os
import shutil
import subprocess
from typing import Dict, Optional

from assistant.tools.models import (
    Result, ErrorCode, CriticalErrorSet, RetryableErrorSet,
    DependencyCheck, logger, ProgressCallback
)


def install_tool(tool: Dict, dry_run: bool = False, progress_callback=None) -> Result:
    """Install one tool. Called ONLY by manager.py.

    Args:
        tool: Tool metadata dict
        dry_run: If True, only return what would be done
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
    if dry_run:
        return Result(
            success=True,
            message=f"Dry run: would install {tool['name']} via {tool['ecosystem']}",
            hint=f"Command: {tool['install_cmd']}",
            stage="install"
        )

    ecosystem = tool["ecosystem"]

    if progress_callback:
        progress_callback(f"Starting installation of {tool['name']}...", 0, 1)

    if ecosystem == "apt":
        return install_apt(tool, sudo=True, progress_callback=progress_callback)
    elif ecosystem == "go":
        return install_go(tool, progress_callback=progress_callback)
    elif ecosystem == "pip":
        return install_pip(tool, progress_callback=progress_callback)
    elif ecosystem == "cargo":
        return install_cargo(tool, progress_callback=progress_callback)
    elif ecosystem == "binary":
        return install_binary(tool, progress_callback=progress_callback)
    elif ecosystem == "script":
        return install_script(tool, progress_callback=progress_callback)
    elif ecosystem == "manual-note":
        return show_manual_instructions(tool)
    else:
        return Result(
            success=False,
            code=ErrorCode.NOT_FOUND,
            message=f"Unsupported ecosystem: {ecosystem}",
            hint=f"Tool {tool['name']} cannot be auto-installed",
            stage="install"
        )


def update_tool(tool: Dict, dry_run: bool = False, progress_callback=None) -> Result:
    """Update one tool to latest version.

    Args:
        tool: Tool metadata dict
        dry_run: If True, only show what would be done
        progress_callback: Optional callback for progress updates

    Returns:
        Result indicating success/failure
    """
    if dry_run:
        return Result(
            success=True,
            message=f"Dry run: would update {tool['name']} via {tool['ecosystem']}",
            stage="update"
        )

    ecosystem = tool["ecosystem"]

    if ecosystem == "apt":
        return update_apt(tool, sudo=True, progress_callback=progress_callback)
    elif ecosystem == "go":
        return update_go(tool, progress_callback=progress_callback)
    elif ecosystem == "pip":
        return update_pip(tool, progress_callback=progress_callback)
    elif ecosystem == "cargo":
        return update_cargo(tool, progress_callback=progress_callback)
    else:
        return Result(
            success=False,
            code=ErrorCode.NOT_FOUND,
            message=f"Update not supported for ecosystem: {ecosystem}",
            hint=f"Tool {tool['name']} cannot be auto-updated",
            stage="update"
        )


def install_apt(tool: Dict, sudo: bool, progress_callback=None) -> Result:
    """Install tool via apt package manager."""
    # Use name as package name if not specified in metadata
    pkg_name = tool.get("package", tool["name"])
    cmd = f"{'sudo ' if sudo else ''}apt install -y {pkg_name}"

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

        if result.returncode != 0:
            stderr = result.stderr.decode()
            error_msg = "Install failed"

            if "Unable to locate package" in stderr:
                error_msg = f"Package {pkg_name} not found in repository"
            elif "Permission denied" in stderr:
                return Result(
                    success=False,
                    code=ErrorCode.PERMISSION_DENIED,
                    message="Permission denied",
                    stderr=stderr,
                    hint="Try running with sudo or as root",
                    stage="install"
                )

            return Result(
                success=False,
                code=ErrorCode.INSTALL_FAILED,
                message=error_msg,
                stderr=stderr,
                hint="Run 'apt update' and try again",
                stage="install"
            )

        return Result(success=True, stage="install")

    except subprocess.TimeoutExpired:
        return Result(
            success=False,
            code=ErrorCode.TIMEOUT,
            message="Installation timeout",
            hint="Network issue or large package",
            stage="install"
        )
    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message=f"Unexpected error: {str(e)}",
            stage="install"
        )


def install_go(tool: Dict, progress_callback=None) -> Result:
    """Install Go tool."""
    cmd = tool['install_cmd']

    try:
        # Go install can take a while
        result = subprocess.run(cmd.split(), capture_output=True, timeout=600)

        if result.returncode != 0:
            return Result(
                success=False,
                code=ErrorCode.INSTALL_FAILED,
                message="Go installation failed",
                stderr=result.stderr.decode(),
                hint="Check Go installation and network connectivity",
                stage="install"
            )

        return Result(success=True, stage="install")

    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message=f"Unexpected error: {str(e)}",
            stage="install"
        )


def install_pip(tool: Dict, progress_callback=None) -> Result:
    """Install Python tool."""
    # Prefer pipx if available, otherwise use pip3 --user
    if shutil.which("pipx"):
        cmd = f"pipx install {tool['name']}"
    else:
        cmd = f"pip3 install --user {tool['name']}"

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=300)

        if result.returncode != 0:
            return Result(
                success=False,
                code=ErrorCode.INSTALL_FAILED,
                message="Pip installation failed",
                stderr=result.stderr.decode(),
                stage="install"
            )

        return Result(success=True, stage="install")
    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message=f"Unexpected error: {str(e)}",
            stage="install"
        )


def install_cargo(tool: Dict, progress_callback=None) -> Result:
    """Install Rust tool via cargo."""
    cmd = f"cargo install {tool['name']}"

    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=600)

        if result.returncode != 0:
            return Result(
                success=False,
                code=ErrorCode.INSTALL_FAILED,
                message="Cargo installation failed",
                stderr=result.stderr.decode(),
                stage="install"
            )

        return Result(success=True, stage="install")
    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message=f"Unexpected error: {str(e)}",
            stage="install"
        )


def install_script(tool: Dict, progress_callback=None) -> Result:
    """Install tool via a shell script (e.g., metasploit)."""
    cmd = tool['install_cmd']
    
    try:
        # Scripts often need shell=True
        result = subprocess.run(cmd, shell=True, capture_output=True, timeout=900)

        if result.returncode != 0:
            return Result(
                success=False,
                code=ErrorCode.INSTALL_FAILED,
                message="Script installation failed",
                stderr=result.stderr.decode(),
                stage="install"
            )

        return Result(success=True, stage="install")
    except Exception as e:
        return Result(
            success=False,
            code=ErrorCode.INSTALL_FAILED,
            message=f"Unexpected error: {str(e)}",
            stage="install"
        )


def install_binary(tool: Dict, progress_callback=None) -> Result:
    """Manual binary installation (placeholder)."""
    return Result(
        success=False,
        code=ErrorCode.NOT_FOUND,
        message="Direct binary installation not yet automated",
        hint=f"Please follow instructions at {tool.get('docs_url', 'documentation')}",
        stage="install"
    )


def show_manual_instructions(tool: Dict) -> Result:
    """Show manual instructions for tools that can't be auto-installed."""
    return Result(
        success=True,
        message=f"Manual instructions for {tool['name']}",
        hint=f"Follow instructions at: {tool.get('docs_url', 'no URL provided')}",
        stage="install"
    )


# Update functions (placeholders/wrappers)
def update_apt(tool: Dict, sudo: bool, progress_callback=None) -> Result:
    return install_apt(tool, sudo, progress_callback)

def update_go(tool: Dict, progress_callback=None) -> Result:
    return install_go(tool, progress_callback)

def update_pip(tool: Dict, progress_callback=None) -> Result:
    return install_pip(tool, progress_callback)

def update_cargo(tool: Dict, progress_callback=None) -> Result:
    return install_cargo(tool, progress_callback)


def install_with_retry(tool: Dict, max_attempts: int = 2, progress_callback=None) -> Result:
    """Install with retry for retryable errors."""
    last_result = Result(success=False, code=ErrorCode.NOT_FOUND, message="Not started")
    for attempt in range(max_attempts):
        last_result = install_tool(tool, progress_callback=progress_callback)
        if last_result.success:
            return last_result
        if last_result.code not in RetryableErrorSet.RETRYABLE:
            break
        logger.info(f"Retryable error, attempt {attempt + 1}/{max_attempts}: {last_result.message}")
    return last_result
