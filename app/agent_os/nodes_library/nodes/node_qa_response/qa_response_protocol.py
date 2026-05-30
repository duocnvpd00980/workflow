# qa_response_protocol.py

from pydantic import BaseModel, Field
from typing import List


class QaResponseOutput(BaseModel):
    answer: str = Field(
        default="Xin lỗi, hệ thống chưa tìm thấy dữ liệu phù hợp để trả lời câu hỏi này.",
        description="Câu trả lời cuối cùng đã được tổng hợp mạch lạc bằng Tiếng Việt dựa trên ngữ cảnh văn bản.",
    )
    source_used: bool = Field(
        default=False,
        description="True nếu câu trả lời dựa vào tài liệu tra cứu (RAG), False nếu là kiến thức chung hoặc tự trả lời.",
    )
    tone: str = Field(
        default="neutral",
        description="Giọng điệu của phản hồi (ví dụ: neutral, professional, friendly).",
    )
    citations: List[str] = Field(
        default_factory=list,
        description="Danh sách các thông tư, quy chế hoặc nguồn tài liệu đã trích dẫn để trả lời.",
    )
