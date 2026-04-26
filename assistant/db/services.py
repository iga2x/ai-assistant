from sqlalchemy.orm import Session
from assistant.db.models import Message, Conversation
from datetime import datetime, timezone

class ConversationService:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create_conversation(self, title: str) -> Conversation:
        conv = self.session.query(Conversation).filter_by(title=title).first()
        if not conv:
            conv = Conversation(title=title)
            self.session.add(conv)
            self.session.commit()
            self.session.refresh(conv)
        return conv

    def save_message(self, conversation_id: int, role: str, content: str) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(msg)
        self.session.commit()
        self.session.refresh(msg)
        return msg

    def get_history(self, conversation_id: int, limit: int = 10):
        msgs = self.session.query(Message).filter_by(
            conversation_id=conversation_id
        ).order_by(Message.created_at.desc()).limit(limit).all()
        return list(reversed(msgs))
