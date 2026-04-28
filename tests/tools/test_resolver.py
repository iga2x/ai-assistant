"""Test tool name resolution and deprecation handling."""

import pytest
from assistant.tools.resolver import Resolver


def test_resolve_normal_tool():
    """Test resolving normal tool name."""
    resolver = Resolver()
    assert resolver.resolve("nmap") == "nmap"
    assert resolver.resolve("nuclei") == "nuclei"


def test_resolve_alias():
    """Test resolving aliased tool name."""
    resolver = Resolver()
    assert resolver.resolve("netcat") == "nc"
    assert resolver.resolve("ncat") == "nc"


def test_resolve_deprecated_with_replacement():
    """Test resolving deprecated tool with replacement."""
    resolver = Resolver()
    assert resolver.resolve("subjack") == "subzy"


def test_resolve_deprecated_without_replacement():
    """Test resolving deprecated tool without replacement."""
    resolver = Resolver()
    assert resolver.resolve("wifitex") is None


def test_get_version_flags_default():
    """Test getting default version flags."""
    resolver = Resolver()
    flags = resolver.get_version_flags("nmap", ["--version", "-V"])
    assert flags == ["--version", "-V"]


def test_get_version_flags_override():
    """Test getting overridden version flags for problematic tools."""
    resolver = Resolver()
    flags = resolver.get_version_flags("assetfinder", ["--version"])
    assert flags == ["--help"]  # Override from BAD_VERSION_CMDS

    flags = resolver.get_version_flags("john", ["--version"])
    assert flags == ["--list=build-info"]  # Override from BAD_VERSION_CMDS


def test_is_deprecated():
    """Test checking if tool is deprecated."""
    resolver = Resolver()
    assert resolver.is_deprecated("wifitex") is True
    assert resolver.is_deprecated("nmap") is False


def test_get_replacement():
    """Test getting replacement for deprecated tool."""
    resolver = Resolver()
    assert resolver.get_replacement("subjack") == "subzy"
    assert resolver.get_replacement("wifitex") is None
    assert resolver.get_replacement("nmap") is None


def test_case_insensitive_resolution():
    """Test case-insensitive name resolution."""
    resolver = Resolver()
    assert resolver.resolve("NETCAT") == "nc"
    assert resolver.resolve("SubJack") == "subzy"
