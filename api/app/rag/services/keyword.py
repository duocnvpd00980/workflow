"""KeywordRAG — phục vụ retrieval topic / SEO / angle.

Chunk: 1 keyword = 1 chunk.
Search: BM25 70 / Vector 30.
"""

from .base import BaseRAG, dedupe_key
from .chunkers import chunk_keyword


class KeywordRAG(BaseRAG):
    source_type = "keyword"

    async def add(self, keyword: str, *, business_id: str, source_id: str) -> str:
        keyword = (keyword or "").strip()
        if not keyword:
            return "skipped"

        dkey = dedupe_key(business_id, self.source_type, source_id)
        chunks = chunk_keyword(keyword)
        records = self._build_records(chunks, business_id, source_id, dkey)
        return await self._store.add_chunks(records, dkey)
