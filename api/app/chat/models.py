from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    UUID, Boolean, DateTime, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


from datetime import datetime, timezone
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

# ── Tự động gắn UTC timezone cho mọi datetime khi load từ DB ──
@event.listens_for(Base, "load", propagate=True)
def _localize_datetimes(target, context):
    for attr in target.__mapper__.column_attrs:
        col = attr.columns[0]
        if isinstance(col.type, DateTime):
            val = getattr(target, attr.key)
            if isinstance(val, datetime) and val.tzinfo is None:
                setattr(target, attr.key, val.replace(tzinfo=timezone.utc))


# ── Conversation ──────────────────────────────────────────
class Conversation(Base):
    __tablename__ = "conversation"
    __table_args__ = (
        Index("ix_conv_last_msg", "last_message_at"),
        Index("ix_conv_created",  "created_at"),
    )

    id:              Mapped[uuid.UUID]     = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    title:           Mapped[str]           = mapped_column(String(255), default="")
    system_prompt:   Mapped[str]           = mapped_column(Text, default="")
    is_archived:     Mapped[bool]          = mapped_column(Boolean, default=False)
    metadata_:       Mapped[dict]          = mapped_column("metadata", JSON, default=dict)
    created_at:      Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())
    updated_at:      Mapped[datetime]      = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    last_message_at: Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())

    messages: Mapped[list[Message]]           = relationship(back_populates="conversation", cascade="all, delete-orphan")
    memories: Mapped[list[ConversationMemory]]= relationship(back_populates="conversation", cascade="all, delete-orphan")

    @property
    def thread_id(self) -> str:
        return f"conv_{self.id}"

    def __repr__(self) -> str:
        return self.title or f"Conversation {self.id}"


# ── Message ───────────────────────────────────────────────
class Message(Base):
    __tablename__ = "message"
    __table_args__ = (
        Index("ix_msg_conv_created", "conversation_id", "created_at"),
        Index("ix_msg_role",         "role"),
        Index("ix_msg_status",       "status"),
    )

    id:              Mapped[uuid.UUID]     = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID]     = mapped_column(ForeignKey("conversation.id", ondelete="CASCADE"))
    role:            Mapped[str]           = mapped_column(String(20))
    status:          Mapped[str]           = mapped_column(String(20), default="completed")
    content:         Mapped[str]           = mapped_column(Text, default="")
    html:            Mapped[str]           = mapped_column(Text, default="")
    node_name:       Mapped[str]           = mapped_column(String(100), default="")
    token_input:     Mapped[int]           = mapped_column(Integer, default=0)
    token_output:    Mapped[int]           = mapped_column(Integer, default=0)
    model_name:      Mapped[str]           = mapped_column(String(100), default="")
    error_message:   Mapped[str]           = mapped_column(Text, default="")
    metadata_:       Mapped[dict]          = mapped_column("metadata", JSON, default=dict)
    created_at:      Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())
    updated_at:      Mapped[datetime]      = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"{self.role} • {self.created_at:%Y-%m-%d %H:%M:%S}"


# ── ConversationMemory ────────────────────────────────────
class ConversationMemory(Base):
    __tablename__ = "conversation_memory"
    __table_args__ = (
        UniqueConstraint("conversation_id", "key"),
        Index("ix_memory_conv_key", "conversation_id", "key"),
    )

    id:              Mapped[uuid.UUID]  = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID]  = mapped_column(ForeignKey("conversation.id", ondelete="CASCADE"))
    key:             Mapped[str]        = mapped_column(String(255))
    value:           Mapped[dict]       = mapped_column(JSON, default=dict)
    created_at:      Mapped[datetime]   = mapped_column(DateTime, server_default=func.now())
    updated_at:      Mapped[datetime]   = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="memories")

    def __repr__(self) -> str:
        return self.key


# ── DocumentSource ────────────────────────────────────────
class DocumentSource(Base):
    __tablename__ = "document_source"
    __table_args__ = (
        Index("ix_doc_status",     "status"),
        Index("ix_doc_created_at", "created_at"),
    )

    id:            Mapped[int]              = mapped_column(Integer, primary_key=True)
    title:         Mapped[str]              = mapped_column(String(512))
    file_path:     Mapped[Optional[str]]    = mapped_column(String(1024), nullable=True)
    status:        Mapped[str]              = mapped_column(String(32), default="pending")
    chunk_count:   Mapped[int]              = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]]    = mapped_column(Text, nullable=True)
    processed_at:  Mapped[Optional[datetime]]= mapped_column(DateTime, nullable=True)
    created_at:    Mapped[datetime]         = mapped_column(DateTime, server_default=func.now())
    updated_at:    Mapped[datetime]         = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def extension(self) -> str:
        from pathlib import Path
        return Path(self.file_path).suffix.lstrip(".") if self.file_path else "unknown"