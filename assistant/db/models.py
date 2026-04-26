from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy import create_engine
from datetime import datetime, timezone
from assistant.utils.paths import DB_PATH

Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String)  # user, assistant, system
    content = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    conversation = relationship("Conversation", back_populates="messages")

class ContextEntity(Base):
    __tablename__ = "context_entities"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True)
    value = Column(String)
    entity_type = Column(String)  # ip, domain, file, target, etc.
    confidence = Column(Float, default=1.0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    description = Column(Text)
    status = Column(String)  # pending, running, completed, failed, cancelled
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    steps = relationship("TaskStep", back_populates="task")

class TaskStep(Base):
    __tablename__ = "task_steps"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    description = Column(Text)
    order = Column(Integer)
    status = Column(String)
    command = Column(Text)  # The actual command executed
    result = Column(Text)
    task = relationship("Task", back_populates="steps")

class ScanSnapshot(Base):
    __tablename__ = "scan_snapshots"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    tool_name = Column(String)
    target = Column(String)
    raw_output = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    services = relationship("Service", back_populates="snapshot")

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey("scan_snapshots.id"))
    port = Column(Integer)
    protocol = Column(String)
    service_name = Column(String)
    version = Column(String)
    state = Column(String)
    snapshot = relationship("ScanSnapshot", back_populates="services")

class ScopeItem(Base):
    __tablename__ = "scope_items"
    id = Column(Integer, primary_key=True)
    target = Column(String, unique=True)
    target_type = Column(String)  # ip, domain, cidr
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DiffReport(Base):
    __tablename__ = "diff_reports"
    id = Column(Integer, primary_key=True)
    old_snapshot_id = Column(Integer, ForeignKey("scan_snapshots.id"))
    new_snapshot_id = Column(Integer, ForeignKey("scan_snapshots.id"))
    diff_data = Column(Text)  # JSON string of differences
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    command = Column(Text)
    status = Column(String)  # allowed, blocked, skipped, success, failed
    exit_code = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}")

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

