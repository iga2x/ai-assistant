import re
from typing import List, Dict, Any
from pydantic import BaseModel

class ParsedService(BaseModel):
    port: int
    protocol: str
    service_name: str
    state: str
    version: str = ""

def parse_nmap_output(output: str) -> List[ParsedService]:
    """
    Parse a simple nmap output table.
    Example:
    80/tcp  open  http
    443/tcp open  https
    """
    services = []
    # Regex to match: port/protocol state service
    pattern = re.compile(r"(\d+)/(\w+)\s+(\w+)\s+(.*)")
    
    for line in output.splitlines():
        match = pattern.search(line)
        if match:
            port, protocol, state, service = match.groups()
            services.append(ParsedService(
                port=int(port),
                protocol=protocol,
                state=state,
                service_name=service.strip()
            ))
    return services
