"""Centralized safety gate - all execution must pass through here."""

import re
import ipaddress
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from assistant.config.manager import ConfigManager


class SafetyDecision(Enum):
    """Safety decision for command execution."""
    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_CONFIRMATION = "require_confirmation"


class RiskLevel(Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SafetyCheckResult:
    """Result of safety check."""
    decision: SafetyDecision
    risk_level: RiskLevel
    reason: str
    target_class: str = "unknown"


@dataclass
class PlanSafetyCheckResult:
    """Result of plan safety check."""
    decision: SafetyDecision
    overall_risk: RiskLevel
    step_decisions: List[SafetyCheckResult]
    reason: str


class SafetyGate:
    """Centralized safety checking. All execution MUST pass through."""

    # Low-risk patterns (safe to auto-approve)
    LOW_RISK_PATTERNS = [
        r'^(hostname|whoami|pwd|ls|date|uptime|echo|cat|head|tail|less|more)(\s|$)',
        r'^ip\s+(addr|link|route)(\s|$)',
        r'^ifconfig\s',
        r'^uname\s',
        r'^df\s',
        r'^free\s',
        r'^whois\s+[a-zA-Z0-9\.-]+',
        r'^dig\s+[a-zA-Z0-9\.-]+',
        r'^nslookup\s+[a-zA-Z0-9\.-]+',
        r'^curl\s+-I\s+',  # HEAD request only
        r'^curl\s+--head\s+',
    ]

    # Dangerous patterns (always block or require confirmation)
    DANGEROUS_PATTERNS = [
        r'rm\s+-rf\s+/',
        r':\(\).*\{.*\|:&.*\}\s*:',  # Fork bomb (matches :(){ :|:& };: pattern)
        r':\(\).*\|:',  # Fork bomb variant
        r'>\s*/dev/sd[a-z]',  # Direct disk write
        r'mkfs\.',  # Filesystem creation
        r'dd\s+if=.*of=/dev',  # Disk destruction
        r'chmod\s+777\s+/',
        r'chown\s+-R\s+.*\s+/',
    ]

    # Target classification patterns
    TARGET_PATTERNS = {
        'public_ip': r'\b(?!(?:127\.|10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.|192\.168\.))(?:\d{1,3}\.){3}\d{1,3}\b',
        'private_ip': r'\b(?:10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.|192\.168\.)\d{1,3}\.\d{1,3}\b',
        'localhost': r'\b(?:127\.0\.0\.1|localhost)\b',
        'domain': r'\b[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.[a-zA-Z]{2,}\b',
        'url': r'https?://[^\s]+',
        'file_path': r'/[^\s]+',
    }

    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for performance."""
        self.low_risk_compiled = [re.compile(p) for p in self.LOW_RISK_PATTERNS]
        self.dangerous_compiled = [re.compile(p) for p in self.DANGEROUS_PATTERNS]
        self.target_compiled = {
            k: re.compile(v) for k, v in self.TARGET_PATTERNS.items()
        }

    def check_command(self, command: str, context: Dict[str, Any] = None) -> SafetyCheckResult:
        """Check if a command is safe to execute.

        Args:
            command: Command string to check
            context: Additional context (user, mode, etc.)

        Returns:
            SafetyCheckResult with decision and reasoning
        """
        context = context or {}

        # 1. Check execution mode FIRST (learning mode bypasses all checks)
        execution_mode = context.get('execution_mode', 'active')
        if execution_mode == 'learning':
            target_class = self._classify_target(command)
            return SafetyCheckResult(
                decision=SafetyDecision.ALLOW,
                risk_level=RiskLevel.LOW,
                reason="Learning mode - simulation only",
                target_class=target_class
            )

        # 2. Check for dangerous patterns
        for pattern in self.dangerous_compiled:
            if pattern.search(command):
                return SafetyCheckResult(
                    decision=SafetyDecision.BLOCK,
                    risk_level=RiskLevel.CRITICAL,
                    reason=f"Command matches dangerous pattern: {pattern.pattern}",
                    target_class=self._classify_target(command)
                )

        # 3. Check for low-risk patterns
        for pattern in self.low_risk_compiled:
            if pattern.match(command):
                return SafetyCheckResult(
                    decision=SafetyDecision.ALLOW,
                    risk_level=RiskLevel.LOW,
                    reason="Command matches low-risk pattern",
                    target_class=self._classify_target(command)
                )

        # 4. Classify target and check risk
        target_class = self._classify_target(command)
        risk_level = self._assess_command_risk(command, target_class)

        # 5. Make decision based on risk
        if risk_level == RiskLevel.LOW:
            return SafetyCheckResult(
                decision=SafetyDecision.ALLOW,
                risk_level=risk_level,
                reason="Low-risk command auto-approved",
                target_class=target_class
            )
        elif risk_level == RiskLevel.MEDIUM:
            return SafetyCheckResult(
                decision=SafetyDecision.REQUIRE_CONFIRMATION,
                risk_level=risk_level,
                reason="Medium-risk command requires confirmation",
                target_class=target_class
            )
        else:
            # HIGH and CRITICAL require confirmation (CRITICAL should have been caught by dangerous patterns)
            return SafetyCheckResult(
                decision=SafetyDecision.REQUIRE_CONFIRMATION,
                risk_level=risk_level,
                reason=f"{risk_level.value}-risk command requires confirmation",
                target_class=target_class
            )

    def _classify_target(self, command: str) -> str:
        """Classify the target type in the command."""
        # Check in order of specificity
        if self.target_compiled['localhost'].search(command):
            return 'localhost'
        if self.target_compiled['private_ip'].search(command):
            return 'private_ip'
        if self.target_compiled['public_ip'].search(command):
            return 'public_ip'
        if self.target_compiled['url'].search(command):
            return 'url'
        if self.target_compiled['domain'].search(command):
            return 'domain'
        if self.target_compiled['file_path'].search(command):
            return 'file_path'

        return 'unknown'

    def _assess_command_risk(self, command: str, target_class: str) -> RiskLevel:
        """Assess the risk level of a command."""
        # High-risk target types
        if target_class == 'public_ip':
            return RiskLevel.HIGH
        if target_class == 'url' and 'http' in command.lower():
            return RiskLevel.MEDIUM

        # Scan tools
        scan_tools = ['nmap', 'masscan', 'rustscan', 'nikto', 'sqlmap']
        if any(tool in command.lower() for tool in scan_tools):
            if target_class == 'localhost':
                return RiskLevel.LOW
            return RiskLevel.MEDIUM

        # Destructive commands
        destructive = ['rm ', 'dd ', 'mkfs', 'format', 'delete']
        if any(cmd in command.lower() for cmd in destructive):
            return RiskLevel.HIGH

        # Default to medium for unknown
        return RiskLevel.MEDIUM

    def execute_with_safety(self, command: str, executor, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute command with automatic safety checks.

        Args:
            command: Command to execute
            executor: Executor function/callable
            context: Additional context

        Returns:
            Execution result with safety decision
        """
        safety_check = self.check_command(command, context)

        if safety_check.decision == SafetyDecision.BLOCK:
            return {
                'success': False,
                'stderr': safety_check.reason,
                'safety_decision': safety_check.decision.value,
                'risk_level': safety_check.risk_level.value
            }

        if safety_check.decision == SafetyDecision.REQUIRE_CONFIRMATION:
            # Caller must handle confirmation
            return {
                'success': False,
                'requires_confirmation': True,
                'reason': safety_check.reason,
                'safety_decision': safety_check.decision.value,
                'risk_level': safety_check.risk_level.value
            }

        # Safe to execute
        try:
            result = executor(command)
            result['safety_decision'] = safety_check.decision.value
            result['risk_level'] = safety_check.risk_level.value
            return result
        except Exception as e:
            return {
                'success': False,
                'stderr': str(e),
                'safety_decision': safety_check.decision.value,
                'risk_level': safety_check.risk_level.value
            }


def safety_check(risk: str = "medium", requires_approval: bool = None):
    """Decorator for declarative safety checking.

    Args:
        risk: Risk level ('low', 'medium', 'high', 'critical')
        requires_approval: Override auto-approval for this function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get safety gate from context or create new one
            safety_gate = kwargs.get('safety_gate') or SafetyGate()

            # Extract command if present
            command = kwargs.get('command', '')
            if not command and args:
                command = str(args[0])

            # Check safety
            check = safety_gate.check_command(command)
            if check.decision == SafetyDecision.BLOCK:
                raise Exception(f"Safety block: {check.reason}")

            if check.decision == SafetyDecision.REQUIRE_CONFIRMATION:
                # Return dict indicating confirmation needed
                return {
                    'requires_confirmation': True,
                    'reason': check.reason,
                    'command': command
                }

            # Execute function
            return func(*args, **kwargs)

        return wrapper
    return decorator
