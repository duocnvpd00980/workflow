from pydantic import BaseModel, Field, ConfigDict


class AuditLogOutput(BaseModel):
    """
    Hợp đồng dữ liệu bất biến cho Node Audit Logger.
    Đảm bảo loại bỏ hoàn toàn các trường dữ liệu rác ngoài đặc tả.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    event_type: str = Field(
        ..., description="Loại sự kiện hệ thống (ví dụ: workflow, tool_call, error)"
    )
    actor: str = Field(
        ..., description="Tác nhân thực thi hành động (ví dụ: system, user, agent_ads)"
    )
    action: str = Field(..., description="Mô tả hành động cụ thể")
    success: bool = Field(default=True, description="Trạng thái thực thi của hành động")
