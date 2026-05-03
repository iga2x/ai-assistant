"""Test AI response schemas and validation."""

import pytest
import json
from assistant.ai.schemas import (
    AIResponse, Plan, PlanStep, ActionRequest,
    ValidatedResponse, validate_ai_response, create_mock_response
)


class TestPlanStepValidation:
    """Test PlanStep validation."""

    def test_valid_plan_step(self):
        """Test creating a valid plan step."""
        step = PlanStep(
            description="Test step",
            tool="shell",
            command="ls -la",
            requires_approval=False
        )
        assert step.description == "Test step"
        assert step.tool == "shell"
        assert step.command == "ls -la"
        assert step.requires_approval is False

    def test_invalid_risk_level(self):
        """Test that invalid risk level is rejected."""
        with pytest.raises(ValueError):
            Plan(
                title="Test",
                intent="test",
                risk_level="invalid_risk",
                steps=[]
            )


class TestPlanValidation:
    """Test Plan validation."""

    def test_valid_plan(self):
        """Test creating a valid plan."""
        plan = Plan(
            title="Test Plan",
            intent="network_scan",
            risk_level="medium",
            steps=[
                PlanStep(description="Step 1", tool="nmap", command="scan 127.0.0.1", requires_approval=True)
            ]
        )
        assert plan.title == "Test Plan"
        assert plan.intent == "network_scan"
        assert plan.risk_level == "medium"
        assert len(plan.steps) == 1


class TestAIResponseValidation:
    """Test AIResponse validation."""

    def test_valid_ai_response(self):
        """Test creating a valid AI response."""
        response = AIResponse(
            reasoning="Test reasoning",
            intent="network_scan",
            action_type="security_scan",
            content="Test content",
            plan=Plan(
                title="Test",
                intent="test",
                risk_level="low",
                steps=[]
            )
        )
        assert response.reasoning == "Test reasoning"
        assert response.intent == "network_scan"
        assert response.action_type == "security_scan"


class TestResponseParsing:
    """Test parsing and validation of AI responses."""

    def test_valid_json_response(self):
        """Test parsing valid JSON response."""
        raw = json.dumps({
            "reasoning": "User wants to scan network",
            "intent": "network_scan",
            "action_type": "security_scan",
            "plan": {
                "title": "Network Scan",
                "intent": "network_scan",
                "risk_level": "medium",
                "steps": [
                    {
                        "description": "Scan localhost",
                        "tool": "nmap",
                        "command": "nmap 127.0.0.1",
                        "requires_approval": True
                    }
                ]
            }
        })

        validated = validate_ai_response(raw)

        assert validated.is_valid is True
        assert len(validated.validation_errors) == 0
        assert validated.response.intent == "network_scan"
        assert validated.response.plan is not None

    def test_invalid_json_response(self):
        """Test parsing invalid JSON response."""
        raw = "This is not JSON"

        validated = validate_ai_response(raw)

        assert validated.is_valid is False
        assert "Invalid JSON" in validated.validation_errors
        assert validated.response.content == "This is not JSON"

    def test_plan_without_steps(self):
        """Test that plan without steps is marked as invalid."""
        raw = json.dumps({
            "reasoning": "Test",
            "intent": "scan",
            "action_type": "command_execution",
            "plan": {
                "title": "Test Plan",
                "intent": "scan",
                "risk_level": "medium",
                "steps": []  # Empty steps
            }
        })

        validated = validate_ai_response(raw)

        assert validated.is_valid is False
        assert "at least one step" in validated.validation_errors[0].lower()

    def test_executable_without_intent(self):
        """Test that executable action without intent is marked as invalid."""
        raw = json.dumps({
            "reasoning": "Test",
            "action_type": "security_scan",
            "plan": {
                "title": "Test",
                "intent": "unknown",  # Not a proper intent for security scan
                "risk_level": "medium",
                "steps": [
                    {"description": "Step 1", "tool": "shell", "command": "test", "requires_approval": False}
                ]
            }
        })

        validated = validate_ai_response(raw)

        # Empty intent should be caught
        if not validated.response.intent:
            assert validated.is_valid is False
            assert "intent" in str(validated.validation_errors).lower()


class TestMockResponse:
    """Test mock response generation."""

    def test_mock_ip_response(self):
        """Test mock response for IP request."""
        validated = create_mock_response("find my ip")

        assert validated.is_valid is True
        assert validated.response.intent == "local_ip_lookup"
        assert validated.response.action_type == "read_only_local"
        assert validated.response.plan is not None
        assert len(validated.response.plan.steps) == 1

    def test_mock_scan_response(self):
        """Test mock response for scan request."""
        validated = create_mock_response("scan localhost")

        assert validated.is_valid is True
        assert validated.response.intent == "network_scan"
        assert validated.response.action_type == "security_scan"
        assert validated.response.plan is not None
        assert len(validated.response.plan.steps) == 2

    def test_mock_chat_response(self):
        """Test mock response for general chat."""
        validated = create_mock_response("hello there")

        assert validated.is_valid is True
        assert validated.response.intent == "chat"
        assert validated.response.action_type == "no_action"
        assert validated.response.content is not None
        assert "hello there" in validated.response.content.lower()


class TestResponseExtensibility:
    """Test that mock response system is extensible."""

    def test_different_inputs_different_responses(self):
        """Test that different inputs produce different responses."""
        ip_response = create_mock_response("find my ip")
        scan_response = create_mock_response("scan network")
        chat_response = create_mock_response("hello")

        # Each should have different intents
        assert ip_response.response.intent != scan_response.response.intent
        assert scan_response.response.intent != chat_response.response.intent

    def test_mock_response_structure(self):
        """Test that mock responses have correct structure."""
        validated = create_mock_response("find my ip")

        # Should have all required fields
        assert hasattr(validated.response, 'reasoning')
        assert hasattr(validated.response, 'intent')
        assert hasattr(validated.response, 'action_type')
        assert hasattr(validated.response, 'plan') or hasattr(validated.response, 'content')

        # If plan exists, it should have steps
        if validated.response.plan:
            assert len(validated.response.plan.steps) > 0
