from pydantic import BaseModel, Field, ConfigDict

class SharedStateOutput(BaseModel):
    """
    Hợp đồng dữ liệu đầu ra đóng băng (Frozen Contract) của Shared State Service.
    Đảm bảo tính bất biến khi chuyển giao trạng thái trên mạng MainBus.
    """
    model_config = ConfigDict(frozen=True, extra="ignore")

    response: str = Field(default="Chào bạn, tôi có thể hỗ trợ gì cho bạn?")
    tone: str = Field(default="neutral")
    input_tokens: int = Field(default=0, description="Số lượng token đầu vào (Observability Metrics).")
    output_tokens: int = Field(default=0, description="Số lượng token đầu ra (Observability Metrics).")