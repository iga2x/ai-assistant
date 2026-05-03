"""Test pronoun resolution with ordered patterns."""

import pytest
from assistant.context.resolver import ContextResolver
from assistant.memory import MemoryManager, EntityStore, EncryptedDB


@pytest.fixture
def memory_manager():
    """Create a test memory manager."""
    return MemoryManager()


@pytest.fixture
def resolver(memory_manager):
    """Create a context resolver with test memory."""
    return ContextResolver(memory_manager.entities)


def test_pronoun_resolution_double_replacement(resolver):
    """Test that 'that same target' doesn't get double replaced."""
    # Set up context
    resolver.store.update("last_target", "192.168.1.1")

    # Test the problematic case
    text = "check that same target"
    resolved = resolver.resolve(text)

    # Should only replace once, not twice
    assert resolved == "check 192.168.1.1 same target"
    assert resolved.count("192.168.1.1") == 1


def test_pronoun_resolution_specific_first(resolver):
    """Test that more specific patterns are matched first."""
    resolver.store.update("last_target", "target.local")
    resolver.store.update("last_ip", "192.168.1.1")

    # "that ip" should be matched, not just "that"
    text = "scan that ip"
    resolved = resolver.resolve(text)

    assert resolved == "scan 192.168.1.1"
    assert "target.local" not in resolved


def test_pronoun_resolution_the_same_target(resolver):
    """Test 'the same target' phrase."""
    resolver.store.update("last_target", "example.com")

    text = "scan the same target again"
    resolved = resolver.resolve(text)

    assert resolved == "scan example.com again"


def test_pronoun_resolution_my_ip(resolver):
    """Test 'my ip' resolution."""
    resolver.store.update("last_ip", "10.0.0.5")

    text = "show my ip"
    resolved = resolver.resolve(text)

    assert resolved == "show 10.0.0.5"


def test_pronoun_resolution_it(resolver):
    """Test 'it' resolution."""
    resolver.store.update("last_target", "localhost")

    text = "scan it"
    resolved = resolver.resolve(text)

    assert resolved == "scan localhost"


def test_pronoun_resolution_no_match(resolver):
    """Test that text without pronouns is unchanged."""
    resolver.store.update("last_target", "example.com")

    text = "scan 192.168.1.1"
    resolved = resolver.resolve(text)

    assert resolved == "scan 192.168.1.1"
    assert "example.com" not in resolved


def test_pronoun_resolution_fallback(resolver):
    """Test fallback when last_target is not set."""
    resolver.store.update("last_ip", "10.0.0.5")

    text = "scan it"
    resolved = resolver.resolve(text)

    # Should not replace 'it' if last_target is not set
    assert resolved == "scan it"
