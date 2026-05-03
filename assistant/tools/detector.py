"""Pure detection engine - INTERNAL USE ONLY (Issue 14 Fix).

This module provides low-level tool detection functions.
DO NOT use directly - use ToolRegistry from assistant.tools.registry instead.

ARCHITECTURE (Issue 14 Fix):
1. detector.py: Low-level detection (INTERNAL - use via ToolRegistry)
2. registry.py: MAIN INTERFACE - use ToolRegistry for discovery and execution
3. manager.py: Lifecycle operations (install/uninstall/update) - use ToolManager

For normal usage:
    from assistant.tools.registry import ToolRegistry
    registry = ToolRegistry.get_global_registry()
    result = registry.detect()
"""

import shutil
import subprocess
import re
from typing import Dict, List, Optional
from packaging.version import parse as parse_version
from packaging.specifiers import SpecifierSet

from assistant.tools.models import (
    ToolInfo, ToolStatus, ErrorCode, Result, logger
)


def detect_tool(metadata: Dict) -> ToolInfo:
    """Pure function. No side effects. No installs. Never mutates metadata.

    Args:
        metadata: Tool metadata dict (name, binary, version_flags, etc.)

    Returns:
        ToolInfo with detection results
    """
    try:
        binary = metadata.get("binary", metadata["name"])
        path = shutil.which(binary)

        if not path:
            return ToolInfo(
                name=metadata["name"],
                status=ToolStatus.NOT_FOUND,
                category=metadata.get("category", "unknown")
            )

        version = get_tool_version(binary, metadata.get("version_flags", ["--version"]))

        # Check if version meets requirements
        status = ToolStatus.INSTALLED
        warning = ""

        if version != "unknown" and "version_required" in metadata:
            if not _meets_version_requirement(version, metadata["version_required"]):
                status = ToolStatus.OUTDATED
                warning = f"Version {version} does not meet requirement {metadata['version_required']}"

        return ToolInfo(
            name=metadata["name"],
            status=status,
            version=version,
            path=path,
            category=metadata.get("category", "unknown"),
            warning=warning
        )

    except PermissionError as e:
        return ToolInfo(
            name=metadata["name"],
            status=ToolStatus.PERMISSION_DENIED,
            category=metadata.get("category", "unknown"),
            error="Permission denied",
            hint="Check file permissions"
        )
    except Exception as e:
        logger.error(f"Error detecting tool {metadata.get('name', 'unknown')}: {e}")
        return ToolInfo(
            name=metadata["name"],
            status=ToolStatus.BROKEN,
            category=metadata.get("category", "unknown"),
            error=f"Detection error: {str(e)}",
            hint="Tool may be corrupted or misconfigured"
        )


def _score_version_match(version: str, output: str, flag: str) -> float:
    """Score how well the version output matches expected patterns.

    Higher score = better match.

    Args:
        version: Extracted version string
        output: Full output from tool
        flag: The flag used to get this output

    Returns:
        Float score (0-100)
    """
    score = 0.0

    # 1. Prefer --version flags (more standard)
    if flag == "--version":
        score += 20
    elif flag == "-V":
        score += 15
    elif flag == "-v":
        score += 10

    # 2. Check if version appears in first few lines (indicates proper version output)
    first_lines = output.split('\n')[:3]
    version_in_output = any(version in line for line in first_lines)
    if version_in_output:
        score += 25

    # 3. Prefer longer version strings (more specific)
    version_parts = version.count('.')
    score += version_parts * 5

    # 4. Bonus for "version" word in output
    if 'version' in output.lower():
        score += 10

    # 5. Penalty if output is too long (likely help text)
    if len(output) > 500:
        score -= 10

    # 6. Penalty if output contains "usage" or "help" indicators
    if any(word in output.lower() for word in ['usage:', 'options:', 'usage:', 'help:']):
        score -= 20

    # 7. Bonus for common version indicators
    if any(indicator in output.lower() for indicator in ['release', 'build', 'compiled', 'version:']):
        score += 15

    return max(0, score)


def get_tool_version(binary: str, version_flags: List[str]) -> str:
    """Try multiple version flags in order, scoring each match.

    Args:
        binary: Tool binary name
        version_flags: List of version flags to try (e.g., ["--version", "-V"])

    Returns:
        Version string or "unknown"
    """
    candidates = []  # Store (score, version, flag) tuples

    for flag in version_flags:
        try:
            result = subprocess.run(
                [binary, flag],
                capture_output=True,
                timeout=10.0
            )

            if result.returncode == 0 or result.stdout or result.stderr:
                stdout = result.stdout.decode(errors='ignore')
                stderr = result.stderr.decode(errors='ignore')

                parsed = parse_version_output(binary, stdout, stderr)
                if parsed != "unknown":
                    # Score the match
                    score = _score_version_match(parsed, stdout + stderr, flag)
                    candidates.append((score, parsed, flag, stdout + stderr))
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            continue
        except Exception as e:
            logger.warning(f"Error checking version for {binary} with flag {flag}: {e}")
            continue

    # Return the highest-scoring candidate
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    # Brute-force fallback: Try common flags if we still don't have a version
    fallback_flags = ["--version", "-version", "-v", "-V", "-h", "--help", "version"]
    # Filter out flags we've already tried
    to_try = [f for f in fallback_flags if f not in version_flags]

    for flag in to_try:
        try:
            # Re-use the same execution logic (simplified for fallback)
            result = subprocess.run([binary, flag], capture_output=True, timeout=5.0)
            
            if result.stdout or result.stderr:
                parsed = parse_version_output(binary, result.stdout.decode(errors='ignore'), result.stderr.decode(errors='ignore'))
                if parsed != "unknown":
                    return parsed
        except:
            continue

    return "unknown"


def parse_version_output(binary: str, stdout: str, stderr: str) -> str:
    """Parse version string from tool output.

    Args:
        binary: Tool binary name
        stdout: Process stdout
        stderr: Process stderr

    Returns:
        Version string or "unknown"
    """
    # Try stdout first
    version = _extract_version(binary, stdout)
    if version != "unknown":
        return version

    # Fallback to stderr
    version = _extract_version(binary, stderr)
    return version


def _extract_version(binary: str, text: str) -> str:
    """Extract version number from text using regex.

    Args:
        binary: Tool binary name
        text: Text to search for version

    Returns:
        Version string or "unknown"
    """
    # Common version patterns
    # Tier 1: Tool-Name Affinity (e.g., "Aircrack-ng 1.7", "Impacket v0.10.0")
    # This is the highest confidence match
    tool_name = binary.split('/')[-1].lower()
    # Handle common name variations and suffixes (e.g., impacket-psexec -> impacket)
    clean_name = tool_name.replace('-ng', '').replace('3', '').replace('v', '')
    base_name = re.split(r'[-_]', clean_name)[0]
    
    name_patterns = [
        rf'{re.escape(tool_name)}.*?(\d+\.\d+[\d.]*)',
        rf'{re.escape(clean_name)}.*?(\d+\.\d+[\d.]*)',
        rf'{re.escape(base_name)}.*?(\d+\.\d+[\d.]*)',
    ]
    
    for p in name_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)

    # Tier 2: High-confidence patterns (e.g., "Version: 1.2", "v1.2")
    # But ignore "Java version", "Python version", etc.
    matches = []
    found = re.finditer(r'(?:version|v|release|rev|build)[:\s]*(\d+\.\d+[\d.]*)', text, re.IGNORECASE)
    for m in found:
        # Check context (avoid "Java version", etc.)
        context = text[max(0, m.start()-20):m.start()].lower()
        if any(bad in context for bad in ('java', 'python', 'kernel', 'linux', 'gcc', 'clang')):
            continue
        return m.group(1)

    # Tier 3: Standalone numbers (fallback)
    found = re.finditer(r'\b(\d+\.\d+[\d.]*)\b', text)
    for m in found:
        val = m.group(1)
        # Check context even for standalone numbers
        context = text[max(0, m.start()-20):m.start()].lower()
        if any(bad in context for bad in ('java', 'python', 'kernel', 'linux', 'gcc', 'clang')):
            continue
            
        # Ignore years
        if val in ("2022", "2023", "2024", "2025", "2026"):
            continue
        return val

    return "unknown"


def _meets_version_requirement(current: str, required: str) -> bool:
    """Check if current version meets requirement (e.g., '>=3.0.0').

    Args:
        current: Current version string
        required: Version requirement (e.g., '>=3.0.0')

    Returns:
        True if version meets requirement
    """
    try:
        if current == "unknown" or not current:
            return False

        # Sanitize version string (strip trailing dots, clean common prefixes)
        clean_current = current.strip().rstrip('.').lstrip('v')
        
        # If it contains extra info (like 4.6.4. (Git v4.6.4)), take just the first part
        clean_current = clean_current.split()[0]

        spec = SpecifierSet(required)
        return parse_version(clean_current) in spec
    except Exception as e:
        logger.debug(f"Failed to compare versions: current={current}, required={required}, error={e}")
        return False

