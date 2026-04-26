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
        try:
            data = json.loads(raw_response)
            content = data.get("content", "")
            intent = data.get("intent")
            reasoning = data.get("reasoning")
            plan = data.get("plan")
            return ParsedAIResponse(
                content=content,
                intent=intent,
                reasoning=reasoning,
                plan=plan,
                raw=raw_response,
                valid_json=True
            )
        except json.JSONDecodeError:
            return ParsedAIResponse(
                content="I understood, but I do not have a clear response.",
                raw=raw_response,
                valid_json=False
            )
