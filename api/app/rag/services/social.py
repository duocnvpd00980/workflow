"""SocialPostRAG — phục vụ retrieval hook / CTA / concept / structure.

Chunk: title / body / CTA -> 3–6 chunk / post.
Search: Vector 60 / BM25 40.
"""

import hashlib

from .base import BaseRAG
from .chunkers import chunk_social


def _social_dedupe_key(business_id: str, source_id: str) -> str:
    raw = f"{business_id}::social::{source_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


class SocialPostRAG(BaseRAG):
    source_type = "social"

    async def add(
        self,
        *,
        business_id: str,
        source_id: str,
        title: str = "",
        body: str = "",
        cta: str = "",
    ) -> str:
        if not (title or body or cta):
            return "skipped"

        dkey = _social_dedupe_key(business_id, source_id)
        chunks = chunk_social(title, body, cta)
        records = self._build_records(chunks, business_id, source_id, dkey)
        return await self._store.add_chunks(records, dkey)
