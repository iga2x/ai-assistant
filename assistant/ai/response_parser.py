# assistant/ai/response_parser.py
import re
from typing import Optional
from assistant.ai.response_types_v2 import StructuredResponse

class ResponseParser:
    """Parse structured fields from AI responses."""

    def parse(self, text: str) -> StructuredResponse:
        """Extract Answer, Command/Example, Details, Next step from text."""
        # Extract Answer (always present)
        answer = self._extract_field(text, ["Answer:", "answer:"])
        if not answer:
            # Fallback: use entire text as answer if no structure found
            answer = text.strip()

        # Extract optional fields
        command = self._extract_field(text, ["Command / Example:", "Command:", "Example:"])
        details = self._extract_field(text, ["Details:", "details:"])
        next_step = self._extract_field(text, ["Next step:", "Next Step:"])

        # Clean code blocks from command
        if command:
            command = self._remove_code_block_markers(command)

        return StructuredResponse(
            answer=answer,
            command=command,
            details=details,
            next_step=next_step
        )

    def _extract_field(self, text: str, labels: list[str]) -> Optional[str]:
        """Extract field content after one of the given labels."""
        for label in labels:
            # Match label, capture content until next label or end (with or without newline)
            pattern = rf"{label}\s*(.+?)(?=\n(?:Answer:|Command|Example|Details:|Next|$)|$)"
            match = re.search(pattern, text, re.DOTALL)
            if match:
                content = match.group(1).strip()
                # Remove trailing empty lines
                return re.sub(r'\n+$', '', content)
        return None

    def _remove_code_block_markers(self, text: str) -> str:
        """Remove ```bash and ``` markers from command text."""
        text = re.sub(r'```\w*\n?', '', text)
        text = re.sub(r'\n?```', '', text)
        return text.strip()
