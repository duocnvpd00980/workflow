# qa_retriever_protocol.py

from pydantic import BaseModel, Field
from typing import List

class QARetrieverOutput(BaseModel):
    search_query: str = Field(
        default="", 
        description="Từ khóa hoặc câu hỏi đã được tối ưu hóa để đưa vào Vector DB tra cứu."
    )
    retrieved_contexts: List[str] = Field(
        default_factory=list, 
        description="Danh sách các đoạn văn bản, thông tư quy chế tìm thấy có độ tương đồng cao nhất."
    )
    score_threshold: float = Field(
        default=0.0, 
        description="Mức điểm tương đồng (Similarity score) thấp nhất được chấp nhận."
    )