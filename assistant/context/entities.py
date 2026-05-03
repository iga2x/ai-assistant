import warnings
from typing import Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from assistant.db.database import DatabaseManager
from assistant.db.models import ContextEntity

# Deprecation warning
warnings.warn(
    "assistant.context.entities.EntityStore is DEPRECATED. "
    "Use assistant.memory.MemoryManager instead.",
    DeprecationWarning,
    stacklevel=2
)

class EntityStore:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.keys = [
            "last_ip", "last_domain", "last_url", 
            "last_file", "last_target", "last_workspace", "last_scan"
        ]
        self.expiry_hours = 24  # Default context expiry

    def update(self, key: str, value: str, confidence: float = 1.0):
        if key in self.keys:
            # Determine entity type from key
            entity_type = key.split('_')[1] if '_' in key else "general"

            # Priority: Only update if new confidence is higher or equal to existing
            with self.db.get_session() as session:
                existing = session.query(ContextEntity).filter_by(key=key).first()
                if existing and existing.confidence > confidence:
                    # Check if old value is very old
                    age = datetime.now(timezone.utc) - existing.updated_at
                    if age < timedelta(minutes=30):
                        return # Keep high confidence recent value

            self.db.set_entity(key, value, entity_type=entity_type, confidence=confidence)

    def get(self, key: str) -> Optional[str]:
        with self.db.get_session() as session:
            entity = session.query(ContextEntity).filter_by(key=key).first()
            if not entity:
                return None

            # Check Expiry (Phase 2.12)
            updated_at = entity.updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)

            age = datetime.now(timezone.utc) - updated_at
            if age > timedelta(hours=self.expiry_hours):
                return None

            # If confidence is too low, treat as missing
            if entity.confidence < 0.4:
                return None

            return entity.value

    def get_all(self) -> Dict[str, str]:
        with self.db.get_session() as session:
            entities = session.query(ContextEntity).all()
            now = datetime.now(timezone.utc)
            result = {}
            for e in entities:
                updated_at = e.updated_at
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)

                if now - updated_at <= timedelta(hours=self.expiry_hours):
                    result[e.key] = e.value
            return result

    def clear(self):
        self.db.clear_entities()


class LongTermMemory:
    def __init__(self):
        from assistant.utils.paths import MEMORY_JSON_PATH
        import json
        self.path = MEMORY_JSON_PATH
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        import json
        if not self.path.exists():
            return {"user": {}, "entities": {}}
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except Exception:
            return {"user": {}, "entities": {}}

    def save(self):
        import json
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def set(self, category: str, key: str, value: Any):
        if category not in self.data:
            self.data[category] = {}
        self.data[category][key] = value
        self.save()

    def get(self, category: str, key: str, default: Any = None) -> Any:
        return self.data.get(category, {}).get(key, default)
