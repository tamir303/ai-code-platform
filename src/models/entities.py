import uuid
from datetime import datetime, UTC
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class UserEntity(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    api_key = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    sessions = relationship("SessionEntity", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("TaskEntity", back_populates="user", cascade="all, delete-orphan")


class SessionEntity(Base):
    __tablename__ = "chat_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    user = relationship("UserEntity", back_populates="sessions")
    messages = relationship(
        "MessageEntity",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="MessageEntity.created_at"
    )


class MessageEntity(Base):
    __tablename__ = "chat_messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "system", "user", "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    session = relationship("SessionEntity", back_populates="messages")


class TaskEntity(Base):
    __tablename__ = "async_tasks"
    id = Column(String(100), primary_key=True)  # Celery Task ID
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    task_type = Column(String(50), nullable=False)
    status = Column(String(30), default="PENDING")
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    user = relationship("UserEntity", back_populates="tasks")
