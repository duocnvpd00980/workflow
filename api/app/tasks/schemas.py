from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Literal

from pydantic import BaseModel, computed_field


class TaskStepOut(BaseModel):
    id: int
    task_id: int
    step_index: int
    message: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    id: int
    source: str
    source_id: str
    content_type: Optional[str]
    title: str
    status: Literal["running", "paused", "completed", "error", "failed", "stopped"]  # ✅ Thêm Literal
    triggered_by: Optional[str]
    steps_done: int
    steps_total: int
    model: Optional[str]
    error_message: Optional[str]
    meta: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime]

    @computed_field
    @property
    def duration_seconds(self) -> Optional[int]:
        if self.finished_at:
            return int((self.finished_at - self.created_at).total_seconds())
        return None

    @computed_field
    @property
    def progress_percent(self) -> int:
        if self.status in ("completed", "failed", "stopped", "paused"):
            return 100
        return 0

    model_config = {"from_attributes": True}


class TaskDetailOut(TaskOut):
    steps: list[TaskStepOut] = []


class TaskListOut(BaseModel):
    items: list[TaskOut]
    total: int
    limit: int
    offset: int


class TaskStopRequest(BaseModel):
    reason: Optional[str] = None


class TaskRetryRequest(BaseModel):
    meta_override: Optional[dict[str, Any]] = None