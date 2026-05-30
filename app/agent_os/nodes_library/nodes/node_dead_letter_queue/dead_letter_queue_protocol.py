from pydantic import BaseModel, Field

class DeadLetterQueueOutput(BaseModel):

    failed_node: str = Field(default="unknown")

    error_code: str = Field(default="UNKNOWN")

    error_message: str = Field(default="captured")

    retryable: bool = Field(default=False)

    fallback_message: str = Field(
        default="Xin lỗi, hệ thống hiện chưa xử lý được yêu cầu."
    )