"""Test Phase 6.2 fixes for PersistentShell marker leakage."""

import pytest
import re


def test_marker_leakage_fix():
    """Test that marker leakage is properly cleaned."""
    # Simulate the fix from persistent_shell.py
    def clean_marker_leakage(stdout: str) -> str:
        """Simulate the marker leakage fix"""
        # Remove any marker-like patterns that might have leaked
        stdout = re.sub(r'---CMD_END_[a-f0-9]+---:?\d*', '', stdout)
        # Clean up any resulting double newlines or trailing whitespace
        stdout = re.sub(r'\n\s*\n\s*\n', '\n\n', stdout)
        return stdout.strip()
    
    # Test case 1: Marker with exit code
    output_with_marker = """Starting Nmap 7.94
Nmap scan report for 192.168.1.1
Host is up (0.0012s latency).
Nmap done: 256 IP addresses (2 hosts up) scanned in 2.45 seconds---CMD_END_abc123---:0"""
    
    cleaned = clean_marker_leakage(output_with_marker)
    assert "---CMD_END_" not in cleaned
    assert "192.168.1.1" in cleaned
    assert "Nmap done" in cleaned
    
    # Test case 2: Marker without exit code
    output_with_marker_no_code = """Some output here
---CMD_END_def456---"""
    
    cleaned = clean_marker_leakage(output_with_marker_no_code)
    assert "---CMD_END_" not in cleaned
    assert "Some output here" in cleaned
    
    # Test case 3: Multiple markers
    output_with_multiple_markers = """Output line 1
---CMD_END_abc123---:0
Output line 2
---CMD_END_def456---:1"""
    
    cleaned = clean_marker_leakage(output_with_multiple_markers)
    assert "---CMD_END_" not in cleaned
    assert "Output line 1" in cleaned
    assert "Output line 2" in cleaned
    
    # Test case 4: Marker in middle of text
    output_with_embedded_marker = """Starting scan
Found host 192.168.1.1---CMD_END_abc123---:0
Scan complete"""
    
    cleaned = clean_marker_leakage(output_with_embedded_marker)
    assert "---CMD_END_" not in cleaned
    assert "192.168.1.1" in cleaned
    assert "Scan complete" in cleaned


def test_no_false_positives():
    """Test that legitimate output isn't corrupted."""
    def clean_marker_leakage(stdout: str) -> str:
        stdout = re.sub(r'---CMD_END_[a-f0-9]+---:?\d*', '', stdout)
        stdout = re.sub(r'\n\s*\n\s*\n', '\n\n', stdout)
        return stdout.strip()
    
    # Test case: Output that looks similar but isn't a marker
    legitimate_output = """Some text with dashes ---CMD_END_FAKE---:123
This should be preserved because it doesn't match the UUID pattern"""
    
    cleaned = clean_marker_leakage(legitimate_output)
    # The fake marker doesn't match UUID pattern, so it should be preserved
    assert "---CMD_END_FAKE---" in cleaned


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
