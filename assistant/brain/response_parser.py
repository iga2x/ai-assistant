from dataclasses import dataclass
from typing import Optional, Any
import json


@dataclass
class ParsedAIResponse:
    content: str
    intent: Optional[str] = None
    reasoning: Optional[str] = None
    plan: Optional[dict] = None
    raw: str = ""
    valid_json: bool = False


class ResponseParser:
    @staticmethod
    def parse_ai_response(raw_response: str) -> ParsedAIResponse:
        pass
