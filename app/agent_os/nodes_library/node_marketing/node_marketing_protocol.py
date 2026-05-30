from pydantic import BaseModel, ConfigDict, Field


class MarketingOutput(BaseModel):
    """
    Contract bất biến định nghĩa dữ liệu đầu ra của nội dung tiếp thị sáng tạo.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    campaign_copy: str = Field(
        ...,
        description="Nội dung bài viết quảng cáo hoặc thông điệp tiếp thị được tạo ra.",
    )
    target_audience: str = Field(
        ..., description="Phân khúc khách hàng mục tiêu được định vị cho nội dung này."
    )
    tone_of_voice: str = Field(
        ...,
        description="Giọng văn chủ đạo được áp dụng (ví dụ: Sáng tạo, Chuyên nghiệp, Hào hứng).",
    )
