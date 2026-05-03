from typing import List, Any, Optional
from assistant.db.models import init_db, Message, Conversation, ContextEntity, Task, TaskStep, ScanSnapshot, Service
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime, timezone
from contextlib import contextmanager


class DatabaseManager:
    def __init__(self):
        # We no longer keep a single persistent session
        pass

    @contextmanager
    def get_session(self):
        """Context manager for database sessions.

        Ensures sessions are properly closed and committed/rolled back.
        """
        session = init_db()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Conversation methods
    def create_conversation(self, title: str = "New Conversation") -> Conversation:
        with self.get_session() as session:
            conv = Conversation(title=title)
            session.add(conv)
            session.flush()
            session.refresh(conv)
            return conv

    def get_or_create_conversation(self, title: str) -> Conversation:
        with self.get_session() as session:
            conv = session.query(Conversation).filter_by(title=title).first()
            if not conv:
                conv = Conversation(title=title)
                session.add(conv)
                session.flush()
                session.refresh(conv)
            return conv

    def log_message(self, conversation_id: int, role: str, content: str):
        with self.get_session() as session:
            msg = Message(conversation_id=conversation_id, role=role, content=content)
            session.add(msg)

    # Context Entity methods
    def set_entity(self, key: str, value: str, entity_type: str = "general", confidence: float = 1.0):
        with self.get_session() as session:
            entity = session.query(ContextEntity).filter_by(key=key).first()
            if entity:
                entity.value = value
                entity.entity_type = entity_type
                entity.confidence = confidence
                entity.updated_at = datetime.now(timezone.utc)
            else:
                entity = ContextEntity(key=key, value=value, entity_type=entity_type, confidence=confidence)
                session.add(entity)

    def get_entity(self, key: str) -> Optional[str]:
        with self.get_session() as session:
            entity = session.query(ContextEntity).filter_by(key=key).first()
            return entity.value if entity else None

    def get_all_entities(self) -> List[ContextEntity]:
        with self.get_session() as session:
            return session.query(ContextEntity).all()

    def clear_entities(self):
        with self.get_session() as session:
            session.query(ContextEntity).delete()

    def log_audit(self, command: str, status: str, exit_code: int = 0):
        from assistant.db.models import AuditLog
        with self.get_session() as session:
            log = AuditLog(command=command, status=status, exit_code=exit_code)
            session.add(log)

    def save_task_plan(self, title: str, steps: List[Any]) -> int:
        """Save a task plan and return the task ID."""
        from assistant.db.models import Task, TaskStep
        with self.get_session() as session:
            task = Task(description=title, status="pending")
            session.add(task)
            session.flush()
            
            for i, step in enumerate(steps):
                db_step = TaskStep(
                    task_id=task.id,
                    description=step.description,
                    order=i,
                    status="pending",
                    command=getattr(step, 'command', '')
                )
                session.add(db_step)
            
            session.refresh(task)
            return task.id
