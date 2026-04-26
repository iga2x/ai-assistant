from assistant.db.models import init_db, Message, Conversation, ContextEntity, Task, TaskStep, ScanSnapshot, Service
from sqlalchemy.orm import Session
from datetime import datetime, timezone

class DatabaseManager:
    def __init__(self):
        self.session: Session = init_db()

    # Conversation methods
    def create_conversation(self, title: str = "New Conversation") -> Conversation:
        conv = Conversation(title=title)
        self.session.add(conv)
        self.session.commit()
        return conv

    def get_or_create_conversation(self, title: str) -> Conversation:
        conv = self.session.query(Conversation).filter_by(title=title).first()
        if not conv:
            conv = self.create_conversation(title)
        return conv

    def log_message(self, conversation_id: int, role: str, content: str):
        msg = Message(conversation_id=conversation_id, role=role, content=content)
        self.session.add(msg)
        self.session.commit()

    # Context Entity methods
    def set_entity(self, key: str, value: str, entity_type: str = "general", confidence: float = 1.0):
        entity = self.session.query(ContextEntity).filter_by(key=key).first()
        if entity:
            entity.value = value
            entity.entity_type = entity_type
            entity.confidence = confidence
            entity.updated_at = datetime.now(timezone.utc)
        else:
            entity = ContextEntity(key=key, value=value, entity_type=entity_type, confidence=confidence)
            self.session.add(entity)
        self.session.commit()

    def get_entity(self, key: str) -> str:
        entity = self.session.query(ContextEntity).filter_by(key=key).first()
        return entity.value if entity else None

    def get_all_entities(self):
        return self.session.query(ContextEntity).all()

    def clear_entities(self):
        self.session.query(ContextEntity).delete()
        self.session.commit()

    def log_audit(self, command: str, status: str, exit_code: int = 0):
        from assistant.db.models import AuditLog
        log = AuditLog(command=command, status=status, exit_code=exit_code)
        self.session.add(log)
        self.session.commit()
