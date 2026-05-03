import os
import httpx
from unittest.mock import patch, MagicMock
from assistant.ai.detector import detect_providers, check_openai

def test_detect_providers():
    providers = detect_providers()
    assert len(providers) > 0
    names = [p.name for p in providers]
    assert "ollama" in names
    assert "openai" in names

def test_openai_key_detection(monkeypatch):
    # Test with key - mock the API call
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"id": "gpt-4"}, {"id": "gpt-3.5-turbo"}]}

    with patch('httpx.get', return_value=mock_response):
        p = check_openai()
        assert p.available is True
        assert len(p.models) > 0

    # Test without key
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    p = check_openai()
    assert p.available is False
