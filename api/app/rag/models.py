from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import Index, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON
from app.db import Base


class DocumentSource(Base):
    __tablename__ = "knowledge_document_source"
    __table_args__ = (
        Index("ix_status", "status"),
        Index("ix_created_at", "created_at"),
        Index("ix_document_type", "document_type"),
        Index("ix_doc_source_business_id", "business_id"),  # ← filter theo business
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # "brand_guideline", "product_knowledge", "competitor_analysis", "web_page"
    document_type: Mapped[str] = mapped_column(String(64), default="product_knowledge")

    # ── Link về Business ─────────────────────────────────────────
    business_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(32), default="pending")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    business = relationship("Business", back_populates="document_sources")
    pages = relationship("DocumentPage", back_populates="source", cascade="all, delete-orphan")

    @property
    def extension(self) -> str:
        return Path(self.file_path).suffix.lstrip(".") if self.file_path else "unknown"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id} title={self.title} type={self.document_type}>"


class DocumentPage(Base):
    """
    Lưu nội dung từng trang được crawl theo nghiệp vụ marketing.
    Mục đích: user xem lại nội dung đã crawl — không ảnh hưởng RAG pipeline.
    Cascade delete: xoá DocumentSource → tự xoá toàn bộ page liên quan.
    """

    __tablename__ = "knowledge_document_page"
    __table_args__ = (
        Index("ix_doc_page_document_id", "document_id"),
        Index("ix_doc_page_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("knowledge_document_source.id", ondelete="CASCADE"),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationship
    source = relationship("DocumentSource", back_populates="pages")

    def __repr__(self) -> str:
        return (
            f"<DocumentPage id={self.id} document_id={self.document_id} "
            f"url={self.url[:60]!r}>"
        )


class ImageSource(Base):
    """Lưu metadata ảnh — vector embed riêng trong ImageRAG."""
    __tablename__ = "knowledge_image_source"
    __table_args__ = (
        Index("ix_image_status", "status"),
        Index("ix_image_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<ImageSource id={self.id} image_id={self.image_id}>"


class HotelRoom(Base):
    """Lưu thông tin phòng khách sạn — crawl từ website."""
    __tablename__ = "hotel_room"
    __table_args__ = (
        Index("ix_hotel_room_type", "room_type"),
        Index("ix_hotel_room_status", "status"),
        Index("ix_hotel_room_created_at", "created_at"),
        Index("ix_hotel_room_business_id", "business_id"),  # ← filter theo business
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Link về Business ─────────────────────────────────────────
    business_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True
    )

    # Identity
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    slug: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # Core
    room_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    bed_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    area_sqm: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Pricing
    price_per_night: Mapped[Optional[float]] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="VND")

    # Media
    image_urls: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Content
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amenities: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    aliases: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(32), default="active")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    business = relationship("Business", back_populates="hotel_rooms")

    def embed_text(self) -> str:
        parts = [self.name]
        if self.aliases:
            parts.extend(self.aliases)
        if self.room_type:
            parts.append(f"loại phòng: {self.room_type}")
        if self.bed_type:
            parts.append(f"giường: {self.bed_type}")
        if self.capacity:
            parts.append(f"sức chứa: {self.capacity} người")
        if self.area_sqm:
            parts.append(f"diện tích: {self.area_sqm}m²")
        if self.price_per_night:
            parts.append(f"giá: {self.price_per_night:,.0f} {self.currency}/đêm")
        if self.amenities:
            parts.append(f"tiện nghi: {', '.join(self.amenities)}")
        if self.description:
            parts.append(self.description[:500])
        return " | ".join(parts)

    def __repr__(self) -> str:
        return f"<HotelRoom id={self.id} name={self.name} type={self.room_type}>"