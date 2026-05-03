"""Test Phase 6.2 fixes for multi-step output aggregation."""

import pytest
from assistant.analysis.synthesizer import _parse_nmap_discovery, _parse_nmap_summary


class TestNmapDiscoveryParser:
    """Test the new host discovery parser."""
    
    def test_parse_discovery_multiple_hosts(self):
        """Test parsing multiple discovered hosts."""
        output = """Starting Nmap 7.94
Nmap scan report for 192.168.1.1
Host is up (0.0012s latency).
Nmap scan report for 192.168.1.100
Host is up (0.0023s latency).
Nmap done: 256 IP addresses (2 hosts up) scanned in 2.45 seconds"""
        
        result = _parse_nmap_discovery(output)
        assert result is not None
        assert "192.168.1.1" in result
        assert "192.168.1.100" in result
        assert "Discovered devices:" in result
    
    def test_parse_discovery_single_host(self):
        """Test parsing single discovered host."""
        output = """Starting Nmap 7.94
Nmap scan report for 192.168.1.1
Host is up (0.0012s latency).
Nmap done: 256 IP addresses (1 host up) scanned in 1.2 seconds"""
        
        result = _parse_nmap_discovery(output)
        assert result is not None
        assert "192.168.1.1" in result
        assert "Discovered devices:" in result
    
    def test_parse_discovery_localhost_only(self):
        """Test parsing when only localhost is found."""
        output = """Starting Nmap 7.94
Nmap scan report for 127.0.0.1
Host is up (0.000010s latency).
Nmap done: 1 IP address (1 host up) scanned in 0.05 seconds"""
        
        result = _parse_nmap_discovery(output)
        assert result is not None
        assert "No additional network devices found" in result
    
    def test_parse_discovery_empty(self):
        """Test parsing empty output."""
        result = _parse_nmap_discovery("")
        assert result is None
    
    def test_parse_discovery_no_hosts(self):
        """Test parsing output with no hosts."""
        output = """Starting Nmap 7.94
Nmap done: 256 IP addresses (0 hosts up) scanned in 2.45 seconds"""
        
        result = _parse_nmap_discovery(output)
        assert result is None


class TestNmapPortScanParser:
    """Test the existing port scan parser."""
    
    def test_parse_ports_open(self):
        """Test parsing open ports."""
        output = """Starting Nmap 7.94
Nmap scan report for localhost (127.0.0.1)
PORT   STATE SERVICE
22/tcp open  ssh
80/tcp open  http
443/tcp open https"""
        
        result = _parse_nmap_summary(output)
        assert result is not None
        assert "22/tcp" in result
        assert "ssh" in result
        assert "80/tcp" in result
        assert "http" in result
        assert "Open ports found:" in result
    
    def test_parse_ports_closed(self):
        """Test parsing closed ports."""
        output = """Starting Nmap 7.94
Nmap scan report for localhost (127.0.0.1)
All 1000 scanned ports on localhost are closed"""
        
        result = _parse_nmap_summary(output)
        assert result is not None
        assert "No open ports" in result or "closed" in result
    
    def test_parse_ports_empty(self):
        """Test parsing empty output."""
        result = _parse_nmap_summary("")
        assert result is None


class TestCombinedParsing:
    """Test combined port and discovery parsing."""
    
    def test_combined_scan_both_types(self):
        """Test that both parsers can work on same output."""
        port_output = """Starting Nmap 7.94
PORT   STATE SERVICE
22/tcp open  ssh
80/tcp open  http"""
        
        discovery_output = """Starting Nmap 7.94
Nmap scan report for 192.168.1.1
Host is up"""
        
        port_result = _parse_nmap_summary(port_output)
        discovery_result = _parse_nmap_discovery(discovery_output)
        
        assert port_result is not None
        assert discovery_result is not None
        assert "22/tcp" in port_result
        assert "192.168.1.1" in discovery_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
