from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class WriterOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho Node Writer.
    Hỗ trợ cả nội dung nháp và tín hiệu cần gọi thêm công cụ (Search Tool).
    """
    draft_content: str = Field(..., description="Nội dung bài viết")
    pending_tool: bool = Field(default=False, description="Cần dùng công cụ tìm kiếm hay không")
    tool_query: Optional[str] = Field(None, description="Câu lệnh tìm kiếm nếu cần")

    model_config = ConfigDict(
        frozen=True,
        extra="ignore" # Lọc bỏ các giải thích thừa từ LLM khi viết bài
    )