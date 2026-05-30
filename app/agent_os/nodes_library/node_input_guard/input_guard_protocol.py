from pydantic import BaseModel, ConfigDict, Field

class InputGuardOutput(BaseModel):
    """
    Contract bất biến định nghĩa dữ liệu đầu ra sau khi qua bộ lọc bảo mật.
    """
    model_config = ConfigDict(frozen=True, extra="ignore")
    
    is_safe: bool = Field(..., description="Cờ xác định dữ liệu đầu vào có an toàn hay không.")
    sanitized_text: str = Field(..., description="Chuỗi văn bản đã được chuẩn hóa và làm sạch.")
    risk_category: str = Field("NONE", description="Phân loại rủi ro nếu phát hiện vi phạm bảo mật.")
    blocked_keyword: str | None = None