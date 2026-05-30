from pydantic import BaseModel, Field, ConfigDict

class AdOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho nội dung quảng cáo.
    Đảm bảo mọi Node tiêu thụ dữ liệu này đều nhận được các trường cố định.
    """
    content: str = Field(..., min_length=1, description="Nội dung bài viết quảng cáo")
    has_cta: bool = Field(default=False, description="Có lời kêu gọi hành động hay không")
    language_detected: str = Field(default="unknown", description="Ngôn ngữ hệ thống nhận diện được")
    model_config = ConfigDict(
        frozen=True,   # Chống sửa đổi dữ liệu sau khi khởi tạo
        extra="ignore" # Bỏ qua các trường thừa từ LLM để tránh rác Bus
    )