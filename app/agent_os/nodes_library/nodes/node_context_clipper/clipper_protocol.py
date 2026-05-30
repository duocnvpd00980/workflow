from pydantic import BaseModel, Field, ConfigDict
from typing import List

class ClipperOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho Node Clipper.
    Dùng để trích xuất các phân đoạn (clips) nội dung quan trọng từ tài liệu gốc.
    """
    source_id: str = Field(..., description="ID của nguồn dữ liệu gốc (ví dụ: bundle_id hoặc doc_id)")
    clips: List[str] = Field(default_factory=list, description="Danh sách các đoạn nội dung đã được trích xuất")
    summary: str = Field(..., description="Bản tóm tắt ngắn gọn nội dung cốt lõi")
    tags: List[str] = Field(default_factory=list, description="Các từ khóa hoặc chủ đề nổi bật của nội dung")

    model_config = ConfigDict(
        frozen=True,
        extra="ignore" # Loại bỏ các phân tích thừa của LLM khi đang trích xuất dữ liệu
    )