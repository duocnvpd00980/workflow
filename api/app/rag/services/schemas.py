"""Cấu trúc dữ liệu dùng xuyên suốt RAG system."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Chunk:
    text: str
    meta: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "score": self.score, "meta": self.meta}


@dataclass
class SearchResult:
    query: str
    chunks: List[Chunk]
    rag_type: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "rag_type": self.rag_type,
            "chunks": [c.to_dict() for c in self.chunks],
        }
