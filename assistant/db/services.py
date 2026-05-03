from sqlalchemy.orm import Session
from assistant.db.models import Message, Conversation
from datetime import datetime, timezone

class ConversationService:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_or_create_conversation(self, title: str) -> Conversation:
        with self.db.get_session() as session:
            conv = session.query(Conversation).filter_by(title=title).first()
            if not conv:
                conv = Conversation(title=title)
                session.add(conv)
                session.flush()
                session.refresh(conv)
            return conv

    def save_message(self, conversation_id: int, role: str, content: str) -> Message:
        with self.db.get_session() as session:
            msg = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                created_at=datetime.now(timezone.utc)
            )
            session.add(msg)
            session.flush()
            session.refresh(msg)
            return msg

    def get_history(self, conversation_id: int, limit: int = 10):
        with self.db.get_session() as session:
            msgs = session.query(Message).filter_by(
                conversation_id=conversation_id
            ).order_by(Message.created_at.desc()).limit(limit).all()
            return list(reversed(msgs))

