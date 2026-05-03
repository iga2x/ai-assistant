import re
from typing import List, Dict, Any
from pydantic import BaseModel

class ParsedService(BaseModel):
    port: int
    protocol: str
    service_name: str
    state: str
    version: str = ""

class ParsedHost(BaseModel):
    ip: str
    status: str
    latency: str = ""

def parse_nmap_output(output: str) -> Dict[str, Any]:
    """
    Parse nmap output for both hosts and services.
    """
    services = []
    hosts = []
    
    # Service pattern: port/protocol state service
    svc_pattern = re.compile(r"(\d+)/(\w+)\s+(\w+)\s+(.*)")
    # Host pattern: Nmap scan report for 192.168.10.1
    host_pattern = re.compile(r"Nmap scan report for\s+([^\s\(\)]+)")

    
    current_host = None
    for line in output.splitlines():
        # Check for host
        host_match = host_pattern.search(line)
        if host_match:
            current_host = host_match.group(1)
            hosts.append(ParsedHost(ip=current_host, status="up"))
            continue
            
        # Check for service
        svc_match = svc_pattern.search(line)
        if svc_match:
            port, protocol, state, service = svc_match.groups()
            services.append(ParsedService(
                port=int(port),
                protocol=protocol,
                state=state,
                service_name=service.strip()
            ))
            
    return {"hosts": hosts, "services": services}

def parse_subdomains(output: str) -> List[str]:
    """Parse output from subfinder, assetfinder, amass (list of domains)."""
    domains = []
    # Pattern: simple domain regex
    pattern = re.compile(r"^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$", re.IGNORECASE)
    for line in output.splitlines():
        target = line.strip()
        if pattern.match(target):
            domains.append(target)
    return list(set(domains))

class SecurityFinding(BaseModel):
    severity: str
    title: str
    target: str
    description: str = ""

def parse_security_findings(output: str) -> List[SecurityFinding]:
    """
    Parse generic security tool output (Nuclei, etc).
    """
    findings = []
    # Pattern: [severity] title [target]
    pattern = re.compile(r"\[(info|low|medium|high|critical)\]\s+([^\s\[]+)\s+\[([^\]]+)\]")
    
    for line in output.splitlines():
        match = pattern.search(line.lower())
        if match:
            sev, title, target = match.groups()
            findings.append(SecurityFinding(
                severity=sev,
                title=title,
                target=target
            ))
    return findings

def parse_arp_scan(output: str) -> List[ParsedHost]:
    """Parse output from arp-scan."""
    hosts = []
    # Pattern: 192.168.1.1  00:11:22:33:44:55  Vendor
    pattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+([0-9a-fA-F:]{17})\s+(.*)")
    for line in output.splitlines():
        match = pattern.search(line)
        if match:
            ip, mac, vendor = match.groups()
            hosts.append(ParsedHost(ip=ip, status="up", latency=vendor))
    return hosts

def parse_ip_neighbor(output: str) -> List[ParsedHost]:
    """Parse output from ip neighbor show."""
    hosts = []
    # Pattern: 192.168.1.1 dev eth0 lladdr 00:11:22:33:44:55 REACHABLE
    pattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+dev\s+\S+\s+lladdr\s+([0-9a-fA-F:]{17})\s+(\S+)")
    for line in output.splitlines():
        match = pattern.search(line)
        if match:
            ip, mac, status = match.groups()
            hosts.append(ParsedHost(ip=ip, status=status.lower()))
    return hosts
