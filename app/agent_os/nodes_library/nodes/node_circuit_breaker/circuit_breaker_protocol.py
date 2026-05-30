from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class CircuitBreakerOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho bộ ngắt mạch (Circuit Breaker).
    Giám sát trạng thái lỗi và ngăn chặn thực thi Node khi đạt ngưỡng giới hạn.
    """
    is_open: bool = Field(default=False, description="Trạng thái cầu chì: True = Ngắt (đang lỗi), False = Đóng (bình thường)")
    failure_count: int = Field(default=0, description="Số lần lỗi liên tiếp hiện tại")
    threshold: int = Field(default=3, description="Ngưỡng lỗi tối đa trước khi ngắt mạch")
    blocked_node: Optional[str] = Field(default=None, description="Tên Node đang bị chặn thực thi")

    model_config = ConfigDict(
        frozen=True,
        extra="ignore" # Loại bỏ rác từ các báo cáo lỗi không cần thiết
    )