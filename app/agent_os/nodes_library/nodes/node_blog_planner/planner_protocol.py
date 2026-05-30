from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional


class BlogPlanOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho kế hoạch bài viết Blog.
    Xác định cấu trúc, từ khóa và các mục chính cần triển khai.
    """

    title_suggestion: str = Field(..., description="Tiêu đề gợi ý cho bài blog")
    target_keywords: List[str] = Field(
        default_factory=list, description="Danh sách từ khóa SEO chủ chốt"
    )
    outline: List[str] = Field(..., description="Dàn ý chi tiết các mục (H2, H3)")
    estimated_word_count: int = Field(
        default=1000, description="Độ dài dự kiến của bài viết"
    )
    research_required: bool = Field(
        default=False, description="Đánh dấu nếu cần tìm kiếm thêm dữ liệu thực tế"
    )

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",  # Tự động loại bỏ các đoạn text giải thích rông dài của LLM
    )
