from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Business(Base):
    """
    Anchor trung tâm — đại diện cho một doanh nghiệp.
    Tất cả Brand, HotelRoom, DocumentSource, PipelineTask,
    WorkflowSession đều FK về business_id này.
    """

    __tablename__ = "businesses"
    __table_args__ = (
        Index("ix_business_name", "name"),
        Index("ix_business_owner", "owner_id"),
        Index("ix_business_status", "status"),
    )

    # ── Identity ────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)          # "Mường Thanh Luxury"
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)  # "muong-thanh-luxury"

    # ── Ownership ────────────────────────────────────────────────
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # ── Business info ────────────────────────────────────────────
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)   # "hotel", "restaurant"
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Status ───────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(String(32), default="active")      # active, inactive, deleted

    # ── Timestamps ───────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # ── Relationships ────────────────────────────────────────────
    brands = relationship("Brand", back_populates="business", cascade="all, delete-orphan")
    pipeline_tasks = relationship("PipelineTask", back_populates="business", cascade="all, delete-orphan")
    hotel_rooms = relationship("HotelRoom", back_populates="business", cascade="all, delete-orphan")
    document_sources = relationship("DocumentSource", back_populates="business", cascade="all, delete-orphan")
    workflow_sessions = relationship("WorkflowSession", back_populates="business", cascade="all, delete-orphan")
    background_tasks = relationship("BackgroundTask", back_populates="business", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Business id={self.id} name={self.name}>"