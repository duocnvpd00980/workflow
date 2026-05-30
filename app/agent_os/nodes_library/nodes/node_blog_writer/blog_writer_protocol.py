from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class WriterOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho các tác vụ Writer/Editor.
    Hỗ trợ trả về nội dung và cơ chế gọi công cụ (Tool Call) nếu thiếu dữ liệu.
    """

    draft_content: str = Field(
        ..., min_length=1, description="Nội dung bản thảo bài viết"
    )
    pending_tool: bool = Field(
        default=False,
        description="Đánh dấu True nếu cần gọi Search Tool để bổ sung dữ liệu",
    )
    tool_query: Optional[str] = Field(
        default=None, description="Câu lệnh tìm kiếm cụ thể nếu pending_tool là True"
    )

    model_config = ConfigDict(
        frozen=True,  # Chống sửa đổi sau khi tạo
        extra="ignore",  # Tự động lọc bỏ các câu giải thích thừa từ LLM
    )
