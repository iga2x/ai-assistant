import pytest
from assistant.brain.response_parser import ResponseParser

def test_pipeline_with_valid_json():
    """Test that valid JSON produces clean content for users."""
    raw_json = '{"reasoning": "User greeting", "intent": "chat_only", "content": "Hello there!", "plan": null}'
    parsed = ResponseParser.parse_ai_response(raw_json)

    # User-facing content is clean
    assert parsed.content == "Hello there!"

    # Debug fields are accessible
    assert parsed.reasoning == "User greeting"
    assert parsed.intent == "chat_only"
    assert parsed.valid_json is True

def test_pipeline_with_plain_text():
    """Test that plain text is handled gracefully."""
    raw_text = "Here's your answer to question."
    parsed = ResponseParser.parse_ai_response(raw_text)

    assert parsed.content == "Here's your answer to question."
    assert parsed.valid_json is False
    assert parsed.intent is None

def test_pipeline_with_missing_content():
    """Test fallback message when content is missing."""
    raw_json = '{"reasoning": "Some reasoning", "intent": "scan", "plan": {"title": "Scan"}}'
    parsed = ResponseParser.parse_ai_response(raw_json)

    assert parsed.content == "I understood, but I do not have a clear response."
    assert parsed.valid_json is True
    assert parsed.intent == "scan"