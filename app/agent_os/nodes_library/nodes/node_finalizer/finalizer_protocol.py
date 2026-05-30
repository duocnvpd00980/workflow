from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class FinalizerOutput(BaseModel):
    """Hợp đồng dữ liệu đầu ra phẳng, đóng băng 100% của tầng Service."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    status: str = Field(description="SUCCESS / FAILED / EMPTY")
    text: str = Field(description="UI OUTPUT SINGLE SOURCE OF TRUTH")
    flow_type: str = Field(
        default="default", description="Luồng nghiệp vụ được phân giải"
    )
    summary_message: str = Field(
        default="Xử lý thành công.", description="Tin nhắn vắn tắt hệ thống"
    )
    error_details: Optional[str] = Field(
        default=None, description="Chi tiết lỗi nếu hệ thống FAILED"
    )
