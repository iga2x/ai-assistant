# assistant/ai/response_types_v2.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ResponseField:
    """Single field in a structured response."""
    name: str
    content: Optional[str]
    required: bool = False

@dataclass
class StructuredResponse:
    """Structured AI response with 4 fields."""
    answer: str
    command: Optional[str] = None
    details: Optional[str] = None
    next_step: Optional[str] = None
