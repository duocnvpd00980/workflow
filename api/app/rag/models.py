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