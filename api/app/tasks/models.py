from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db import Base


class BackgroundTask(Base):
    """
    Bảng trung tâm theo dõi mọi tác vụ chạy nền trong hệ thống.
    Mỗi module (marketing, research, rag) tạo 1 row khi bắt đầu chạy,
    cập nhật status khi xong — không ảnh hưởng logic xử lý của từng module.
    """

    __tablename__ = "background_tasks"
    __table_args__ = (
        Index("ix_bg_task_status", "status"),
        Index("ix_bg_task_source", "source"),
        Index("ix_bg_task_created_at", "created_at"),
        Index("ix_bg_task_business_id", "business_id"),  # ← filter theo business
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Link về Business ─────────────────────────────────────────
    business_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True
    )

    # Định danh nguồn gốc — để UI link về đúng trang
    source: Mapped[str] = mapped_column(String(32))       # "marketing" | "research" | "rag"
    source_id: Mapped[str] = mapped_column(String(64))    # id gốc của từng module

    # Thông tin hiển thị
    title: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="running")
    # "running" | "completed" | "failed" | "stopped"

    triggered_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Tiến độ — tuỳ module điền, không bắt buộc
    steps_done: Mapped[int] = mapped_column(Integer, default=0)
    steps_total: Mapped[int] = mapped_column(Integer, default=0)

    # Model AI đang dùng nếu có
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Lỗi nếu failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    business = relationship("Business", back_populates="background_tasks")

    def __repr__(self) -> str:
        return (
            f"<BackgroundTask id={self.id} source={self.source} "
            f"source_id={self.source_id} status={self.status}>"
        )