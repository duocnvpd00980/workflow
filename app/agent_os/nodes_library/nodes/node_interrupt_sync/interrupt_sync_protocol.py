from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional


class InterruptSyncOutput(BaseModel):
    """
    Barrier synchronization contract cho parallel workflow.
    """

    # Các branch được yêu cầu chạy
    active_branches: List[str] = Field(
        default_factory=list,
        description="Danh sách branch cần hoàn thành",
    )

    # Các branch đã hoàn thành
    completed_modules: List[str] = Field(
        default_factory=list,
        description="Danh sách branch đã hoàn thành",
    )

    # Các branch còn thiếu
    pending_modules: List[str] = Field(
        default_factory=list,
        description="Danh sách branch còn thiếu",
    )

    # Barrier status
    is_sync_complete: bool = Field(
        default=False,
        description="Tất cả branch đã hoàn thành chưa",
    )

    # Human approval
    requires_approval: bool = Field(
        default=False,
        description="Có yêu cầu user approval không",
    )

    is_approved: bool = Field(
        default=False,
        description="User đã approve chưa",
    )

    # Metadata
    synchronization_mode: str = Field(
        default="dynamic_barrier",
    )

    checkpoint_note: Optional[str] = Field(
        default=None,
    )

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
    )
