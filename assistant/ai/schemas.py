"""AI response schemas with validation."""

from pydantic import BaseModel, Field, field_validator, model_validator

from typing import List, Optional, Any, Dict
from enum import Enum


class IntentCategory(str, Enum):
    """Standard intent categories."""
    CHAT = "chat"
    LOCAL_SYSTEM_INFO = "local_system_info"
    LOCAL_IP_LOOKUP = "local_ip_lookup"
    PUBLIC_IP_LOOKUP = "public_ip_lookup"
    DATE_TIME_LOOKUP = "date_time_lookup"
    TOOL_HELP = "tool_help"
    FILE_READ = "file_read"
    FILE_MODIFY = "file_modify"
    NETWORK_SCAN = "network_scan"
    WEB_REQUEST = "web_request"
    REPORT_GENERATION = "report_generation"
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    """Action type classification."""
    NO_ACTION = "no_action"
    READ_ONLY_LOCAL = "read_only_local"
    BENIGN_WEB_LOOKUP = "benign_web_lookup"
    COMMAND_EXECUTION = "command_execution"
    SECURITY_SCAN = "security_scan"
    FILE_WRITE = "file_write"
    DESTRUCTIVE_ACTION = "destructive_action"
    CLOUD_SEND = "cloud_send"


class TargetClass(str, Enum):
    """Target classification."""
    NONE = "none"
    LOCAL_MACHINE = "local_machine"
    LOCAL_PRIVATE_IP = "local_private_ip"
    LOCAL_PRIVATE_SUBNET = "local_private_subnet"
    PRIVATE_NONLOCAL_TARGET = "private_nonlocal_target"
    PUBLIC_IP = "public_ip"
    PUBLIC_DOMAIN = "public_domain"
    FILE_PATH = "file_path"
    URL = "url"
    UNKNOWN = "unknown"


class PlanStep(BaseModel):
    """Single step in a plan."""
    description: str = Field(..., description="Clear explanation of the step")
    tool: str = Field(default="shell", description="Tool to use for this step")
    command: str = Field(default="", description="Exact command to execute")
    requires_approval: bool = Field(default=True, description="Whether this step needs user approval")
    status: str = Field(default="pending", description="Step status: pending, completed, failed, skipped")
    order: int = Field(default=0, description="Step execution order")


class Plan(BaseModel):
    """Execution plan for a request."""
    title: str = Field(..., description="Short descriptive title of the plan")
    intent: str = Field(default="task", description="Specific intent of the plan")
    risk_level: str = Field(default="low", description="Risk level: low, medium, high, critical")
    risk_summary: str = Field(default="", description="Brief explanation of the risk")
    requires_approval: bool = Field(default=False, description="Whether plan needs approval")
    needs_analysis: bool = Field(default=False, description="Whether the results of this plan need final AI analysis/synthesis")
    steps: List[PlanStep] = Field(default_factory=list, description="Steps in the plan")

    @field_validator('intent')
    @classmethod
    def validate_intent(cls, v):
        if not v:
            return "task"
        return v

    @field_validator('risk_level')
    @classmethod
    def validate_risk_level(cls, v):
        valid_levels = ["low", "medium", "high", "critical"]
        if v not in valid_levels:
            raise ValueError(f'risk_level must be one of {valid_levels}')
        return v


class ActionRequest(BaseModel):
    """Action request parsed from AI response."""
    action_type: str = Field(..., description="Type of action to take")
    intent: str = Field(..., description="Specific intent")
    target_class: str = Field(default="none", description="Class of target")
    params: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")
    reasoning: str = Field(default="", description="AI reasoning for this action")
    data: Optional[Any] = Field(default=None, description="Additional data")


class ActionResult(BaseModel):
    """Result of an action execution."""
    success: bool
    output: str
    data: Optional[Any] = None
    error: Optional[str] = None
    action_type: str
    intent: str



class AIResponse(BaseModel):
    """Validated AI response."""
    reasoning: str = Field(default="The user is engaging in general conversation.", description="AI's reasoning for the response")

    intent: Optional[str] = Field(default="chat", description="Detected intent")
    action_type: Optional[str] = Field(default="no_action", description="Detected action type")
    target_class: Optional[str] = Field(default="none", description="Detected target class")
    content: Optional[str] = Field(default=None, description="Response content for chat")

    plan: Optional[Plan] = Field(default=None, description="Execution plan if applicable")
    raw: str = Field(default="", description="Original raw response")
    
    @model_validator(mode='after')
    def ensure_content(self) -> 'AIResponse':
        if self.content is None:
            if self.plan and self.plan.title:
                self.content = f"Proceeding with: {self.plan.title}"
            else:
                self.content = ""
        return self


    @field_validator('action_type')
    @classmethod
    def validate_action_type(cls, v):
        if v is None:
            return v
        
        # Map aliases
        v = v.lower().strip()
        mapping = {
            "read_only": ActionType.READ_ONLY_LOCAL.value,
            "readonly": ActionType.READ_ONLY_LOCAL.value,
            "read_only_local": ActionType.READ_ONLY_LOCAL.value,
            "command": ActionType.COMMAND_EXECUTION.value,
            "execute": ActionType.COMMAND_EXECUTION.value,
            "scan": ActionType.SECURITY_SCAN.value,
            "security": ActionType.SECURITY_SCAN.value
        }
        
        if v in mapping:
            return mapping[v]

        try:
            ActionType(v)
        except ValueError:
            # If not in enum, default to command_execution if it looks like one, or NO_ACTION
            return ActionType.COMMAND_EXECUTION.value
        return v


    @field_validator('intent')
    @classmethod
    def validate_intent(cls, v):
        if v is None:
            return v
        # Allow both enum values and string values
        try:
            IntentCategory(v)
        except ValueError:
            # If not in enum, still accept it (custom intents allowed)
            pass
        return v


class ValidatedResponse(BaseModel):
    """Wrapper for validated AI response with metadata."""
    response: AIResponse = Field(..., description="Validated AI response")
    is_valid: bool = Field(..., description="Whether response is valid JSON")
    validation_errors: List[str] = Field(default_factory=list, description="Any validation errors")
    source: str = Field(default="unknown", description="Source of response: ai, mock, fallback")


def validate_ai_response(raw_response: str) -> ValidatedResponse:
    """Validate and parse AI response.

    Args:
        raw_response: Raw JSON string from AI

    Returns:
        ValidatedResponse with parsed response and validation status
    """
    import json

    try:
        data = json.loads(raw_response)

        # Validate using Pydantic
        ai_response = AIResponse(raw=raw_response, **data)

        # Additional business logic validation
        errors = []

        # If there's a plan, it must have steps
        if ai_response.plan and not ai_response.plan.steps:
            errors.append("Plan must have at least one step")

        # If action_type is executable, there must be an intent
        if ai_response.action_type in [ActionType.COMMAND_EXECUTION, ActionType.SECURITY_SCAN]:
            if not ai_response.intent:
                errors.append("Executable actions must have an intent")

        # If there's content but no plan, that's fine (chat response)
        # If there's a plan but no content, also fine (will execute)

        return ValidatedResponse(
            response=ai_response,
            is_valid=len(errors) == 0,
            validation_errors=errors,
            source="ai"
        )

    except json.JSONDecodeError as e:
        # Non-JSON response - treat as chat
        return ValidatedResponse(
            response=AIResponse(
                reasoning="AI returned text response",
                content=raw_response.strip() if raw_response.strip() else "I understood, but I do not have a clear response.",
                raw=raw_response
            ),
            is_valid=False,
            validation_errors=["Invalid JSON"],
            source="ai"
        )
    except Exception as e:
        # Validation error
        from assistant.utils.logger import get_logger
        logger = get_logger("ai.schemas")
        logger.warning(f"AI response validation failed: {e}. Raw: {raw_response[:100]}...")
        return ValidatedResponse(
            response=AIResponse(
                reasoning=f"Validation failed: {str(e)}",
                content="I received a technical response from the AI that I couldn't validate. Please try rephrasing your request.",
                raw=raw_response
            ),
            is_valid=False,
            validation_errors=[str(e)],
            source="ai"
        )




def create_mock_response(user_input: str) -> ValidatedResponse:
    """Create a mock response for testing/fallback using the MockRegistry.

    Args:
        user_input: User's input string

    Returns:
        ValidatedResponse with mock AI response
    """
    from assistant.ai.mocks import MockRegistry
    
    response = MockRegistry.get_response(user_input)
    
    if response:
        return ValidatedResponse(
            response=response,
            is_valid=True,
            validation_errors=[],
            source="mock"
        )

    # Default chat response
    return ValidatedResponse(
        response=AIResponse(
            reasoning="The user is engaging in general conversation.",
            intent="chat",
            action_type="no_action",
            content=f"I'm in offline mode. You said: {user_input}",
            raw=""
        ),
        is_valid=True,
        validation_errors=[],
        source="mock"
    )

