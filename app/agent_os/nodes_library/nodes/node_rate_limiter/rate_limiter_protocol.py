from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class RateLimitOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho Bộ giới hạn tần suất (Rate Limiter).
    Đảm bảo hệ thống không gửi yêu cầu vượt quá ngưỡng cho phép của nhà cung cấp API.
    """

    allowed: bool = Field(
        ..., description="Quyền thực thi: True nếu được phép chạy tiếp"
    )
    current_requests: int = Field(
        ..., description="Số lượng request đã thực hiện trong khung giờ hiện tại"
    )
    limit_per_minute: int = Field(
        ..., description="Ngưỡng giới hạn request trên mỗi phút"
    )
    remaining_requests: int = Field(
        default=0, description="Số lượng request còn lại trước khi chạm ngưỡng"
    )
    blocked_reason: Optional[str] = Field(
        default=None,
        description="Lý do bị chặn (ví dụ: 'TPM Limit Reached' hoặc 'RPM Warning')",
    )

    model_config = ConfigDict(frozen=True, extra="ignore")
