# db/models.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import Index, Integer, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class DocumentSource(Base):
    __tablename__ = "knowledge_document_source"
    __table_args__ = (
        Index("ix_status", "status"),
        Index("ix_created_at", "created_at"),
    )

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True)
    title:         Mapped[str]           = mapped_column(String(512))
    file_path:     Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    status:        Mapped[str]           = mapped_column(String(32), default="pending")
    chunk_count:   Mapped[int]           = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at:    Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())
    updated_at:    Mapped[datetime]      = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    processed_at:  Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    @property
    def extension(self) -> str:
        return Path(self.file_path).suffix.lstrip(".") if self.file_path else "unknown"

    def __repr__(self) -> str:
        return self.title