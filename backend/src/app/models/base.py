"""Database models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    type_annotation_map = {
        dict[str, Any]: SQLiteJSON,
    }


class TimestampMixin:
    """Mixin adding created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class User(Base, TimestampMixin):
    """User account model."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(100), default="User")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")


class Conversation(Base, TimestampMixin):
    """AI conversation thread."""

    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conversation_user", "user_id"),
        Index("idx_conversation_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), default="New Conversation")
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    user: Mapped[User | None] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base, TimestampMixin):
    """Chat message in a conversation."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_message_conversation", "conversation_id"),
        Index("idx_message_role", "role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system, tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class WorkspaceMemory(Base, TimestampMixin):
    """Workspace-level memory entries."""

    __tablename__ = "workspace_memory"
    __table_args__ = (
        Index("idx_ws_memory_workspace", "workspace_id"),
        Index("idx_ws_memory_key", "memory_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    memory_key: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[bytes | None] = mapped_column("embedding", JSON, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmbeddingIndex(Base, TimestampMixin):
    """Vector embedding storage for code and documents."""

    __tablename__ = "embeddings"
    __table_args__ = (
        Index("idx_embedding_type", "embed_type"),
        Index("idx_embedding_source", "source"),
        Index("idx_embedding_workspace", "workspace_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    embed_type: Mapped[str] = mapped_column(String(50), nullable=False)  # code, doc, chat
    source: Mapped[str] = mapped_column(String(500), nullable=False)  # file path or message id
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[bytes | None] = mapped_column("embedding", JSON, nullable=True)
    tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)


class AgentTask(Base, TimestampMixin):
    """Agent task execution tracking."""

    __tablename__ = "agent_tasks"
    __table_args__ = (
        Index("idx_task_conversation", "conversation_id"),
        Index("idx_task_status", "status"),
        Index("idx_task_workspace", "workspace_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed, cancelled
    plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    execution_log: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, default=list)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)


class FileSnapshot(Base, TimestampMixin):
    """File state snapshots for rollback."""

    __tablename__ = "file_snapshots"
    __table_args__ = (
        Index("idx_snapshot_workspace", "workspace_id"),
        Index("idx_snapshot_task", "task_id"),
        Index("idx_snapshot_path", "file_path"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # created, modified, deleted
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    