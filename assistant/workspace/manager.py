import os
from pathlib import Path
from datetime import datetime
from assistant.utils.paths import BASE_DIR

class WorkspaceManager:
    def __init__(self):
        self.workspaces_root = BASE_DIR / "workspaces"
        self._ensure_root()

    def _ensure_root(self):
        if not self.workspaces_root.exists():
            self.workspaces_root.mkdir(parents=True, exist_ok=True)

    def get_target_workspace(self, target: str) -> Path:
        """Get or create a directory for a specific target."""
        # Sanitize target for folder name
        safe_target = target.replace("/", "_").replace(" ", "_").replace(":", "_")
        target_dir = self.workspaces_root / safe_target
        
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            
        return target_dir

    def create_session_dir(self, target: str) -> Path:
        """Create a timestamped session directory within a target workspace."""
        target_dir = self.get_target_workspace(target)
        session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = target_dir / session_name
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def list_workspaces(self):
        if not self.workspaces_root.exists():
            return []
        return [d.name for d in self.workspaces_root.iterdir() if d.is_dir()]
