"""Fast path intent classification to avoid unnecessary AI calls for simple inputs.

DEPRECATED: This module is obsolete as of 2026-05-03.
The fast path bypass has been removed from the orchestrator to eliminate fake AI behavior.
All user input now goes through the AI pipeline.

This module is kept for backward compatibility but should not be used in new code.
"""

import re
import warnings
from assistant.ai.response_types import IntentResult


class IntentAnalyzer:
    """DEPRECATED: Classifies user intent BEFORE AI call for fast path optimization.

    This class is obsolete. The fast path has been removed to ensure all chat
    goes through the AI pipeline instead of returning hardcoded responses.
    """
    """Classifies user intent BEFORE AI call for fast path optimization."""

    # Simple greeting patterns
    GREETING_PATTERNS = [
        r'^\s*(hi|hello|hey|yo)[!\.?\s]*$',
        r'^\s*(how\s+are\s+you)[!\.?\s]*$',
        r'^\s*(what\s+(?:can|i)\s+you\s+(?:do|help))[!\.?\s]*$',
    ]

    # Question/explanation patterns
    QUESTION_PATTERNS = [
        r'^\s*(explain|describe)[!\.?\s]',
        r'^\s*(tell\s+me\s+about)[!\.?\s]',
    ]

    # Multi-intent patterns
    MULTI_INTENT_SEPARATORS = [
        r'\s+(?:and|then|followed\s+by|after\s+that)[,\s]*',
        r',\s+(?!and|then)',
    ]

    def classify(self, user_input: str) -> IntentResult:
        """Classify intent using regex/heuristic patterns for fast path.

        DEPRECATED: This method is obsolete. Do not use.
        All intent classification should now happen through the AI pipeline.

        Returns:
            IntentResult with type classification and fast_path flag
        """
        warnings.warn(
            "IntentAnalyzer.classify() is deprecated. "
            "Use the AI pipeline for all intent classification.",
            DeprecationWarning,
            stacklevel=2
        )

        input_lower = user_input.strip().lower()

        # 1. Check for greetings (fastest path)
        for pattern in self.GREETING_PATTERNS:
            if re.match(pattern, input_lower):
                return IntentResult(
                    type="chat",
                    fast_path=True,
                    confidence=0.95
                )

        # 2. Check for questions/explanations (fast path)
        for pattern in self.QUESTION_PATTERNS:
            if re.match(pattern, input_lower):
                return IntentResult(
                    type="chat",
                    fast_path=True,
                    confidence=0.90
                )

        # 3. Check for multi-intent requests (needs full AI)
        for pattern in self.MULTI_INTENT_SEPARATORS:
            if re.search(pattern, user_input):
                return IntentResult(
                    type="multi_task",
                    fast_path=False,
                    confidence=0.85
                )

        # 4. Default: unknown, needs full AI planning
        return IntentResult(
            type="unknown",
            fast_path=False,
            confidence=0.0
        )
