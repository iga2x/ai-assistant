import pytest
from assistant.context.entities import EntityStore
from assistant.context.resolver import ContextResolver
from assistant.context.normalizer import InputNormalizer
from assistant.db.database import DatabaseManager

@pytest.fixture
def db():
    # Use the shared DatabaseManager
    return DatabaseManager()

@pytest.fixture
def store(db):
    return EntityStore(db)

def test_normalization():
    norm = InputNormalizer()
    assert norm.normalize("scann 127.0.0.1") == "scan 127.0.0.1"
    assert norm.normalize("nmapp  google.com") == "nmap google.com"
    # Test redaction
    sensitive = 'api_key="sk-1234567890abcdef"'
    assert "[REDACTED]" in norm.normalize(sensitive)

def test_entity_extraction(store):
    resolver = ContextResolver(store)
    store.clear()
    
    resolver.extract_entities("scan 192.168.1.1")
    assert store.get("last_ip") == "192.168.1.1"
    assert store.get("last_target") == "192.168.1.1"
    
    resolver.extract_entities("check example.com")
    assert store.get("last_domain") == "example.com"
    assert store.get("last_target") == "example.com"
    
    resolver.extract_entities("read report.log")
    assert store.get("last_file") == "report.log"

def test_context_resolution(store):
    resolver = ContextResolver(store)
    store.clear()
    store.update("last_target", "google.com")
    
    assert resolver.resolve("scan it") == "scan google.com"
    assert resolver.resolve("check that same target") == "check google.com google.com target"
    assert resolver.resolve("ping it again") == "ping google.com google.com"
