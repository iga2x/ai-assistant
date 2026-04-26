import pytest
from assistant.brain.response_parser import ResponseParser


def test_parse_valid_json_with_content():
    raw = '{"reasoning": "User asked for help", "intent": "chat_only", "content": "Hello! How can I help?", "plan": null}'
    result = ResponseParser.parse_ai_response(raw)
    assert result.content == "Hello! How can I help?"
    assert result.intent == "chat_only"
    assert result.reasoning == "User asked for help"
    assert result.plan is None
    assert result.raw == raw
    assert result.valid_json is True


def test_parse_json_missing_content():
    raw = '{"reasoning": "User asked", "intent": "chat_only", "plan": {"title": "Test"}}'
    result = ResponseParser.parse_ai_response(raw)
    assert result.content == "I understood, but I do not have a clear response."
    assert result.valid_json is True


def test_parse_plain_text():
    raw = "Hello! How can I help you today?"
    result = ResponseParser.parse_ai_response(raw)
    assert result.content == "Hello! How can I help you today?"
    assert result.valid_json is False
    assert result.intent is None


def test_parse_empty_response():
    raw = ""
    result = ResponseParser.parse_ai_response(raw)
    assert result.content == "I understood, but I do not have a clear response."
    assert result.valid_json is False
