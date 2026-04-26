import platform
import os
from assistant.system.discovery import discover_system, get_shell_info
from assistant.system.os_detect import get_os_detailed
from assistant.system.permissions import is_admin

def test_discover_system():
    info = discover_system()
    assert info.os_name == platform.system()
    assert info.hostname is not None
    assert info.cpu_count > 0
    assert info.total_ram_gb > 0
    assert isinstance(info.is_admin, bool)

def test_get_shell_info():
    shell_info = get_shell_info()
    assert "shell" in shell_info
    assert "shell_path" in shell_info
    assert "terminal" in shell_info

def test_os_detailed():
    os_info = get_os_detailed()
    assert platform.system() in os_info or "macOS" in os_info or "Windows" in os_info

def test_permissions_check():
    # Should run without error
    admin = is_admin()
    assert isinstance(admin, bool)
