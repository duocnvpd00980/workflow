from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import Index, Integer, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from sqlalchemy.types import JSON

class Base(DeclarativeBase):
    pass

class DocumentSource(Base):
    __tablename__ = "knowledge_document_source"
    __table_args__ = (
        Index("ix_status", "status"),
        Index("ix_created_at", "created_at"),
        Index("ix_document_type", "document_type"), # Đảm bảo truy vấn filter loại tài liệu nhanh
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    # "brand_guideline", "product_knowledge", "competitor_analysis", "web_page"
    document_type: Mapped[str] = mapped_column(String(64), default="product_knowledge") 
    
    status: Mapped[str] = mapped_column(String(32), default="pending")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

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

    # Metadata trích xuất thêm: word_count, first_line, source_url, v.v.
    extracted: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

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
    image_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)  # uuid hoặc slug
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)   # URL hoặc path
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
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Identity
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    slug: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # Core
    room_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)   # standard, deluxe, vip, suite
    bed_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)    # single, double, twin, king
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)       # số người
    area_sqm: Mapped[Optional[float]] = mapped_column(nullable=True)              # diện tích m²

    # Pricing
    price_per_night: Mapped[Optional[float]] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="VND")

    # Media
    image_urls: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)       # ["url1", "url2"]

    # Content — dùng để embed
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amenities: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)        # ["wifi", "ac", "bathtub"]
    aliases: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)          # ["phòng đôi tiêu chuẩn", "phòng 2 giường"]

    # Status
    status: Mapped[str] = mapped_column(String(32), default="active")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def embed_text(self) -> str:
        """Text dùng để tạo embedding — combine các field quan trọng + aliases tiếng Việt."""
        parts = [self.name]
        if self.aliases:
            # Alias tiếng Việt giúp search đa ngôn ngữ match được
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