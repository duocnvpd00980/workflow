# =========================================================
# FILE:
# agent_os/nodes_library/node_knowledge_retriever/knowledge_protocol.py
# =========================================================

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    text: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeRetrieverOutput(BaseModel):

    success: bool = True

    query: str = ""

    retrieved_chunks: List[RetrievedChunk] = Field(
        default_factory=list
    )

    total_chunks: int = 0

    doc_type: Optional[str] = None

    error: Optional[str] = None