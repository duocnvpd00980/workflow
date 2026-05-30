# ruff: noqa: E501
from pydantic import BaseModel, Field
from typing import List, Optional


class RetrievalRouterInput(BaseModel):
    query: str = Field(..., description="Câu hỏi gốc từ người dùng cần xử lý tri thức")
    intent_context: Optional[str] = Field(
        default="qa", description="Ngữ cảnh intent từ Policy Engine"
    )


class RetrievalRouterOutput(BaseModel):
    rewritten_query: str = Field(
        ..., description="Câu hỏi đã được tối ưu hóa/bóc tách từ khóa cho Vector DB"
    )
    retrieval_needed: bool = Field(
        default=True, description="Đèn xanh kích hoạt tầng QAR cào dữ liệu"
    )
    search_namespaces: List[str] = Field(
        default_factory=lambda: ["default_knowledge"],
        description="Các phân vùng Vector DB cần quét",
    )
    # ✅ FIX CHÍ MẠNG: Loại bỏ max_digits để trả float về đúng bản chất thuần chủng của nó
    confidence_score: float = Field(
        default=1.0,
        description="Điểm số tin cậy của phân tích định tuyến (Giá trị từ 0.0 đến 1.0)",
    )
