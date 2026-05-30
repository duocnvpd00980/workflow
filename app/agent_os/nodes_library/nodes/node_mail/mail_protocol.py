from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class MailOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho Node Email Writer.
    Định nghĩa cấu trúc một email marketing chuyên nghiệp.
    """
    subject: str = Field(..., description="Tiêu đề email gây ấn tượng (Subject Line)")
    preview_text: Optional[str] = Field(None, description="Đoạn văn bản xem trước (Preheader)")
    body_content: str = Field(..., description="Nội dung chính của email (định dạng Markdown hoặc HTML)")
    call_to_action: str = Field(..., description="Lời kêu gọi hành động (ví dụ: Link đăng ký, nút mua hàng)")
    
    # Phân loại và tối ưu
    email_type: str = Field(default="nurturing", description="Loại email: cold_outreach, newsletter, nurturing, sales")
    target_audience: Optional[str] = Field(None, description="Đối tượng độc giả mục tiêu")
    estimated_reading_time: int = Field(default=1, description="Thời gian đọc ước tính (phút)")

    model_config = ConfigDict(
        frozen=True,
        extra="ignore"
    )