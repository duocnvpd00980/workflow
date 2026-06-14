from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class BackgroundTask(Base):
    __tablename__ = "background_tasks"
    __table_args__ = (
        Index("ix_bg_task_status", "status"),
        Index("ix_bg_task_source", "source"),
        Index("ix_bg_task_created_at", "created_at"),
        Index("ix_bg_task_content_type", "content_type"),
        Index("ix_bg_task_business_id", "business_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    business_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True
    )

    source: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(64))
    content_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="running")
    triggered_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    steps_done: Mapped[int] = mapped_column(Integer, default=0)
    steps_total: Mapped[int] = mapped_column(Integer, default=0)
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    business = relationship("Business", back_populates="background_tasks")
    steps: Mapped[list["TaskStep"]] = relationship(
        "TaskStep",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskStep.created_at",
    )

    def __repr__(self) -> str:
        return f"<BackgroundTask id={self.id} source={self.source} status={self.status}>"


class TaskStep(Base):
    __tablename__ = "task_steps"
    __table_args__ = (Index("ix_task_step_task_id", "task_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("background_tasks.id", ondelete="CASCADE"), nullable=False
    )

    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    task: Mapped["BackgroundTask"] = relationship("BackgroundTask", back_populates="steps")

    def __repr__(self) -> str:
        return f"<TaskStep task_id={self.task_id} step={self.step_index} status={self.status}>"