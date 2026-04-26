import os
from assistant.ai.detector import detect_providers, check_openai

def test_detect_providers():
    providers = detect_providers()
    assert len(providers) > 0
    names = [p.name for p in providers]
    assert "ollama" in names
    assert "openai" in names

def test_openai_key_detection(monkeypatch):
    # Test with key
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    p = check_openai()
    assert p.available is True
    
    # Test without key
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    p = check_openai()
    assert p.available is False
