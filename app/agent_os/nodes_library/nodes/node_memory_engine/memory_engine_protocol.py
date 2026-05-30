from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

class MemoryEntry(BaseModel):
    """Định dạng một mục ghi nhớ đơn lẻ."""
    node_id: str = Field(..., description="ID của Node tạo ra ký ức này")
    content: Any = Field(..., description="Dữ liệu cần ghi nhớ")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Thời điểm ghi nhớ"
    )

class MemoryEngineOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho Memory Engine.
    Quản lý việc truy xuất và cập nhật bộ nhớ của Workflow.
    """
    # 1. Truy xuất (Retrieval)
    short_term_history: List[MemoryEntry] = Field(
        default_factory=list, 
        description="Lịch sử các bước chạy gần nhất trong thread hiện tại"
    )
    
    # 2. Ngữ cảnh (Context)
    context_window: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Các thông tin quan trọng được trích lọc để đưa vào Prompt của Agent tiếp theo"
    )

    # 3. Trạng thái (Status)
    memory_efficiency_score: float = Field(
        default=1.0, 
        description="Chỉ số đánh giá độ liên quan của bộ nhớ (0.0 - 1.0)"
    )

    model_config = ConfigDict(
        frozen=True,
        extra="ignore" # Lọc bỏ các metadata rác từ vector database hoặc cache
    )