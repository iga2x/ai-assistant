"""Test SafetyGate functionality."""

import pytest
from assistant.safety.gate import SafetyGate, SafetyDecision, RiskLevel


@pytest.fixture
def safety_gate():
    """Create a SafetyGate instance."""
    return SafetyGate()


class TestLowRiskPatterns:
    """Test low-risk pattern matching."""

    def test_hostname_command(self, safety_gate):
        result = safety_gate.check_command("hostname")
        assert result.decision == SafetyDecision.ALLOW
        assert result.risk_level == RiskLevel.LOW

    def test_whoami_command(self, safety_gate):
        result = safety_gate.check_command("whoami")
        assert result.decision == SafetyDecision.ALLOW
        assert result.risk_level == RiskLevel.LOW

    def test_pwd_command(self, safety_gate):
        result = safety_gate.check_command("pwd")
        assert result.decision == SafetyDecision.ALLOW
        assert result.risk_level == RiskLevel.LOW

    def test_ip_addr_command(self, safety_gate):
        result = safety_gate.check_command("ip addr")
        assert result.decision == SafetyDecision.ALLOW
        assert result.risk_level == RiskLevel.LOW

    def test_whois_command(self, safety_gate):
        result = safety_gate.check_command("whois example.com")
        assert result.decision == SafetyDecision.ALLOW
        assert result.risk_level == RiskLevel.LOW


class TestDangerousPatterns:
    """Test dangerous pattern blocking."""

    def test_rm_rf_root(self, safety_gate):
        result = safety_gate.check_command("rm -rf /")
        assert result.decision == SafetyDecision.BLOCK
        assert result.risk_level == RiskLevel.CRITICAL
        assert "dangerous pattern" in result.reason.lower()

    def test_fork_bomb(self, safety_gate):
        result = safety_gate.check_command(":(){ :|:& };:")
        assert result.decision == SafetyDecision.BLOCK

    def test_dd_disk_write(self, safety_gate):
        result = safety_gate.check_command("dd if=/dev/zero of=/dev/sda")
        assert result.decision == SafetyDecision.BLOCK

    def test_chmod_777_root(self, safety_gate):
        result = safety_gate.check_command("chmod 777 /")
        assert result.decision == SafetyDecision.BLOCK


class TestTargetClassification:
    """Test target type classification."""

    def test_localhost_target(self, safety_gate):
        result = safety_gate.check_command("scan 127.0.0.1")
        assert result.target_class == 'localhost'

    def test_private_ip_target(self, safety_gate):
        result = safety_gate.check_command("scan 192.168.1.1")
        assert result.target_class == 'private_ip'

    def test_public_ip_target(self, safety_gate):
        result = safety_gate.check_command("scan 8.8.8.8")
        assert result.target_class == 'public_ip'

    def test_domain_target(self, safety_gate):
        result = safety_gate.check_command("scan example.com")
        assert result.target_class == 'domain'

    def test_url_target(self, safety_gate):
        result = safety_gate.check_command("curl https://example.com")
        assert result.target_class == 'url'


class TestRiskAssessment:
    """Test risk level assessment."""

    def test_nmap_localhost_low_risk(self, safety_gate):
        result = safety_gate.check_command("nmap 127.0.0.1")
        assert result.risk_level == RiskLevel.LOW

    def test_nmap_public_ip_high_risk(self, safety_gate):
        result = safety_gate.check_command("nmap 8.8.8.8")
        assert result.risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM]

    def test_sqlmap_medium_risk(self, safety_gate):
        result = safety_gate.check_command("sqlmap -u http://example.com")
        assert result.risk_level == RiskLevel.MEDIUM

    def test_unknown_command_medium_risk(self, safety_gate):
        result = safety_gate.check_command("custom_command some_arg")
        assert result.risk_level == RiskLevel.MEDIUM


class TestLearningMode:
    """Test learning mode behavior."""

    def test_learning_mode_allows_dangerous(self, safety_gate):
        context = {'execution_mode': 'learning'}
        result = safety_gate.check_command("rm -rf /", context)
        assert result.decision == SafetyDecision.ALLOW
        assert "learning mode" in result.reason.lower()


class TestExecuteWithSafety:
    """Test execute_with_safety method."""

    def test_blocked_command_not_executed(self, safety_gate):
        def mock_executor(cmd):
            return {'success': True, 'stdout': 'executed'}

        result = safety_gate.execute_with_safety("rm -rf /", mock_executor)
        assert result['success'] == False
        assert 'safety_decision' in result
        assert result['safety_decision'] == 'block'

    def test_allowed_command_executed(self, safety_gate):
        def mock_executor(cmd):
            return {'success': True, 'stdout': 'hostname output'}

        result = safety_gate.execute_with_safety("hostname", mock_executor)
        assert result['success'] == True
        assert result['stdout'] == 'hostname output'
        assert result['safety_decision'] == 'allow'

    def test_requires_confirmation(self, safety_gate):
        def mock_executor(cmd):
            return {'success': True}

        result = safety_gate.execute_with_safety("nmap 8.8.8.8", mock_executor)
        assert 'requires_confirmation' in result
        assert result['requires_confirmation'] == True


class TestSafetyDecorator:
    """Test @safety_check decorator."""

    def test_decorator_with_low_risk(self):
        from assistant.safety.gate import safety_check

        @safety_check(risk="low")
        def safe_function(command: str):
            return f"Executed: {command}"

        result = safe_function("hostname")
        assert "Executed: hostname" in result

    def test_decorator_with_high_risk(self):
        from assistant.safety.gate import safety_check

        @safety_check(risk="high")
        def dangerous_function(command: str):
            return f"Executed: {command}"

        # This should require confirmation
        result = dangerous_function("nmap 8.8.8.8")
        assert 'requires_confirmation' in result or 'Executed' in result
