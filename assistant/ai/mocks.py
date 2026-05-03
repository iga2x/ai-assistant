from typing import Dict, Any, List, Optional
from assistant.ai.schemas import AIResponse, Plan, PlanStep

class MockRegistry:
    """Registry for AI mock responses to decouple them from the core schema."""
    
    _patterns: Dict[str, AIResponse] = {}
    
    @classmethod
    def register(cls, keyword: str, response: AIResponse):
        cls._patterns[keyword.lower()] = response
        
    @classmethod
    def get_response(cls, user_input: str) -> Optional[AIResponse]:
        lower_input = user_input.lower()
        for keyword, response in cls._patterns.items():
            if keyword in lower_input:
                return response
        return None

# Seed the registry with default mocks
MockRegistry.register("ip", AIResponse(
    reasoning="The user wants to find their IP. This is a safe system query.",
    intent="local_ip_lookup",
    action_type="read_only_local",
    content="To find your IP address, you can use these commands:\n\n1. Local IP: `hostname -I` or `ip addr show`\n2. Public IP: `curl ifconfig.me` or `curl ipinfo.io/ip`\n\nThe hostname -I command shows all local network interfaces, while curl commands query external services for your public IP.",
    plan=Plan(
        title="IP Detection",
        intent="local_ip_lookup",
        risk_level="low",
        steps=[
            PlanStep(
                description="Get local IP",
                command="hostname -I",
                tool="shell",
                requires_approval=False
            )
        ]
    )
))

MockRegistry.register("scan", AIResponse(
    reasoning="The user wants to run a network scan. This is an executable action.",
    intent="network_scan",
    action_type="security_scan",
    content="To find open ports on your network, you can use these tools:\n\n1. **nmap** (most comprehensive):\n   - Quick scan: `nmap -F <target>`\n   - Full port scan: `nmap -p- <target>`\n   - Service detection: `nmap -sV <target>`\n\n2. **ss** (fast, Linux native):\n   - `sudo ss -tuln` shows all listening ports\n   - `sudo ss -tulpn` shows with process names\n\n3. **netstat** (older but still works):\n   - `sudo netstat -tuln`\n   - `sudo netstat -tulpn`\n\n4. **lsof** (shows open files including network sockets):\n   - `sudo lsof -i -P -n | grep LISTEN`\n\nFor network discovery, consider: `nmap -sn 192.168.1.0/24` to find active hosts.",
    plan=Plan(
        title="Network Scan",
        intent="network_scan",
        risk_level="medium",
        risk_summary="Runs an active scan which might be logged.",
        steps=[
            PlanStep(
                description="Ping localhost",
                command="ping -c 1 127.0.0.1",
                tool="shell",
                requires_approval=False
            ),
            PlanStep(
                description="Scan localhost",
                command="nmap -F 127.0.0.1",
                tool="nmap",
                requires_approval=True
            )
        ]
    )
))

MockRegistry.register("how to", AIResponse(
    reasoning="The user is asking for a 'how to' explanation.",
    intent="concept_explanation",
    action_type="no_action",
    content="I'd be happy to help! Please provide more details about what you'd like to learn how to do. For example:\n\n- 'how to find open ports'\n- 'how to scan my network'\n- 'how to check my IP'\n\nI'll provide step-by-step explanations with commands you can use.",
    plan=None
))
