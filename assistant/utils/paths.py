import os
from pathlib import Path

# Base directory for user data
# Support override for testing/restricted environments
_default_home = Path.home() / ".assistant"
BASE_DIR = Path(os.getenv("ASSISTANT_HOME", str(_default_home)))

# Fallback to local directory if home is not writable
try:
    if not BASE_DIR.exists():
        BASE_DIR.mkdir(parents=True, exist_ok=True)
except (OSError, PermissionError):
    BASE_DIR = Path.cwd() / ".assistant"

# Subdirectories as defined in the blueprint
CONFIG_DIR = BASE_DIR
DB_PATH = BASE_DIR / "assistant.db"
LOGS_DIR = BASE_DIR / "logs"
WORKSPACES_DIR = BASE_DIR / "workspaces"
PLUGINS_DIR = BASE_DIR / "plugins"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CACHE_DIR = BASE_DIR / "cache"
SYSTEM_PROFILE_PATH = BASE_DIR / "system_profile.json"
MEMORY_JSON_PATH = BASE_DIR / "memory.json"
MEMORY_DB_PATH = BASE_DIR / "memory.db"
CONFIG_FILE = BASE_DIR / "config.yaml"

def ensure_dirs():
    """Ensure all required user data directories exist."""
    dirs = [
        BASE_DIR,
        LOGS_DIR,
        WORKSPACES_DIR,
        PLUGINS_DIR,
        KNOWLEDGE_DIR,
        CACHE_DIR,
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

def get_log_file():
    """Return the path to the current log file."""
    return LOGS_DIR / "assistant.log"
