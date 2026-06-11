from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, computed_field


class TaskOut(BaseModel):
    id: int
    source: str          # "marketing" | "research" | "rag"
    source_id: str
    title: str
    status: str          # "running" | "completed" | "failed" | "stopped"
    triggered_by: Optional[str]
    steps_done: int
    steps_total: int
    model: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime]

    @computed_field
    @property
    def duration_seconds(self) -> Optional[int]:
        """Tính thời gian chạy (giây). None nếu đang chạy."""
        if self.finished_at:
            return int((self.finished_at - self.created_at).total_seconds())
        return None

    model_config = {"from_attributes": True}


class TaskListOut(BaseModel):
    items: list[TaskOut]
    total: int
    limit: int
    offset: int
