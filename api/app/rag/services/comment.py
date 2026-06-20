"""CommentRAG — phục vụ retrieval insight / customer voice / nhu cầu.

Chunk: 1 comment = 1 chunk, KHÔNG cắt câu.
Search: Vector 80 / BM25 20.
"""

from .base import BaseRAG, dedupe_key
from .chunkers import chunk_comment


class CommentRAG(BaseRAG):
    source_type = "comment"

    async def add(self, comment: str, *, business_id: str, source_id: str) -> str:
        comment = (comment or "").strip()
        if not comment:
            return "skipped"

        dkey = dedupe_key(business_id, self.source_type, source_id)
        chunks = chunk_comment(comment)
        records = self._build_records(chunks, business_id, source_id, dkey)
        return await self._store.add_chunks(records, dkey)
