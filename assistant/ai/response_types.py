"""Unified pipeline response types with strict separation of user-visible vs internal data."""

from dataclasses import dataclass, field
from typing import Literal, Optional, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.tasks.task_types import Plan
    from assistant.actions.executor import ExecutionResult


@dataclass
class PipelineResult:
    """Normalized response from pipeline that separates user-visible content from internal data.

    UI Layer MUST ONLY render user_visible_content.
    Internal fields (internal_reasoning, debug) are for logging/debug only.
    """
    type: Literal["chat", "plan", "approval_required", "execution_result", "clarification", "error"]
    user_visible_content: str
    internal_reasoning: str = ""
    plan: Optional['Plan'] = None
    execution_results: Optional['ExecutionResult'] = None
    requires_approval: bool = False
    risk_level: str = "low"
    debug: dict = field(default_factory=dict)


@dataclass
class IntentResult:
    """Result of intent classification before AI call."""
    type: Literal["chat", "task", "multi_task", "unknown"]
    fast_path: bool = False
    confidence: float = 0.0
