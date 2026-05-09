from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class FactType(str, Enum):
    LOCAL_IP = "local_ip"
    INTERFACE = "interface"
    GATEWAY = "gateway"
    DNS_SERVER = "dns_server"
    LISTENING_PORT = "listening_port"
    OPEN_PORT = "open_port"
    SERVICE = "service"
    PROCESS = "process"
    HOST_DISCOVERED = "host_discovered"
    MAC_ADDRESS = "mac_address"
    VENDOR = "vendor"
    COMMAND_FAILURE = "command_failure"
    WARNING = "warning"
    UNKNOWN_OUTPUT = "unknown_output"


@dataclass
class Fact:
    type: str | FactType
    value: Any
    source_command: Optional[str] = None
    source_step: Optional[str] = None
    confidence: float = 1.0
    raw_excerpt: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
