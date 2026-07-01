"""BaseRAG — phần chung cho 3 loại RAG: build record, search, stats."""

import hashlib
from typing import Dict, List, Optional

from .config import FINAL_K, PERSIST_ROOT, WEIGHTS
from .schemas import Chunk
from .store import FaissMetaStore


def dedupe_key(business_id: str, source_type: str, source_id: str) -> str:
    """Khóa idempotent: add lại cùng (business_id, source_type, source_id) -> duplicate."""
    raw = f"{business_id}::{source_type}::{source_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


class BaseRAG:
    source_type: str = "base"

    def __init__(self):
        weights = WEIGHTS[self.source_type]
        persist_dir = PERSIST_ROOT / self.source_type
        self._store = FaissMetaStore(
            name=self.source_type,
            persist_dir=persist_dir,
            weight_vector=weights["vector"],
            weight_bm25=weights["bm25"],
        )

    def _build_records(
        self,
        chunks: List[Dict],
        business_id: str,
        source_id: str,
        dkey: str,
    ) -> List[Dict]:
        records = []
        for i, c in enumerate(chunks):
            records.append(
                {
                    "text": c["text"],
                    "chunk_type": c.get("chunk_type"),
                    "chunk_id": f"{dkey}_{i}",
                    "business_id": business_id,
                    "source_id": source_id,
                    "source_type": self.source_type,
                }
            )
        return records

    async def search(
        self,
        query: str,
        business_id: Optional[str] = None,
        top_k: int = FINAL_K,
    ) -> List[Chunk]:
        return await self._store.search(query, business_id=business_id, top_k=top_k)

    def stats(self) -> dict:
        return self._store.stats()
    
    def list_all(
        self,
        business_id: Optional[str] = None,
        chunk_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        return self._store.list_all(business_id, chunk_type, limit, offset)
