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
    assert norm.normalize("nmapp  target.local") == "nmap target.local"
    # Test redaction
    sensitive = 'api_key="sk-1234567890abcdef"'
    assert "[REDACTED]" in norm.normalize(sensitive)

def test_entity_extraction(store):
    resolver = ContextResolver(store)
    store.clear()
    
    resolver.extract_entities("scan 192.168.1.1")
    assert store.get("last_ip") == "192.168.1.1"
    assert store.get("last_target") == "192.168.1.1"
    
    resolver.extract_entities("check target.local")
    assert store.get("last_domain") == "target.local"
    assert store.get("last_target") == "target.local"
    
    resolver.extract_entities("read report.log")
    assert store.get("last_file") == "report.log"

def test_context_resolution(store):
    resolver = ContextResolver(store)
    store.clear()
    store.update("last_target", "target.com")
    
    assert resolver.resolve("scan it") == "scan target.com"
    assert resolver.resolve("check that same target") == "check target.com target.com target"
    assert resolver.resolve("ping it again") == "ping target.com target.com"
