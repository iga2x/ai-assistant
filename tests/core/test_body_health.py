import os
from pathlib import Path
from assistant.utils.paths import CONFIG_FILE, DB_PATH, LOGS_DIR, WORKSPACES_DIR
from assistant.db.database import DatabaseManager

def test_config_exists():
    assert Path(CONFIG_FILE).exists()

def test_db_connect():
    db = DatabaseManager()
    # Test that we can get a session
    with db.get_session() as session:
        assert session is not None
        # Test a simple query
        from assistant.db.models import Conversation
        count = session.query(Conversation).count()
        assert count >= 0

def test_logs_writable():
    assert os.access(LOGS_DIR, os.W_OK)

def test_workspace_writable():
    assert os.access(WORKSPACES_DIR, os.W_OK)
