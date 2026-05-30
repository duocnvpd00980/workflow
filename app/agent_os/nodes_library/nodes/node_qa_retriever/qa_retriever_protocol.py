# /app/agent_os/system/knowledge/qa_retriever_protocol.py
from __future__ import annotations
from litellm import ConfigDict
from pydantic import BaseModel, Field
from typing import List, Dict, Any


class HypotheticalDocOutput(BaseModel):
    hypothetical_text: str = Field(default="Thông tin liên quan đến quy định và chính sách công ty.")
    model_config = ConfigDict(extra="allow")
    
class QARetrievalRequest(BaseModel):
    query: str = Field(..., description="Câu hỏi gốc từ người dùng")
    top_k: int = Field(default=3, description="Số lượng chunk cần lấy")

class QARetrievedChunk(BaseModel):
    score: float
    text: str
    parent_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class QARetrievalResult(BaseModel):
    query: str
    chunks: List[QARetrievedChunk] = Field(default_factory=list)