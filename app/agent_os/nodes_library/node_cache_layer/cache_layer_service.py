"""CacheLayerService v2.1 — Answer Cache L3.
Chỉ cache câu trả lời đã generate. Không dùng llama-index, không dùng FAISS.
L1: In-memory LRU | L2: SQLite persistent.
"""

import os
import sqlite3
import hashlib
import logging
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from difflib import SequenceMatcher

from .cache_layer_protocol import CacheLayerOutput

logger = logging.getLogger(__name__)

BASE_DIR = Path(os.getcwd())
CACHE_DB = BASE_DIR / "cache_answers.db"
L1_MAX_SIZE = 1000
FUZZY_THRESHOLD = 0.95


@dataclass
class _L1Entry:
    answer: str
    timestamp: float


class CacheLayerService:
    """
    Answer Cache L3: L1 in-memory LRU + L2 SQLite.
    Flow: L1 hit → return. L1 miss → L2 exact → return. L2 miss → L2 fuzzy → return.
    Tất cả miss → RAG generate → lưu L1 + L2.
    """

    def __init__(self, ttl_hours: int = 24, max_entries: int = 10000):
        self._ttl_seconds = ttl_hours * 3600
        self._max_entries = max_entries
        self._l1: dict[str, _L1Entry] = {}
        self._l1_order: list[str] = []

        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(CACHE_DB), timeout=5.0) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS answer_cache (
                    query_hash TEXT PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    hit_count INTEGER DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created ON answer_cache(created_at)
            """)
            conn.commit()

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:32]

    def _fuzzy_match(
        self, query: str, candidates: list[tuple[str, str]]
    ) -> Optional[tuple[str, float]]:
        query_lower = query.strip().lower()
        best = None
        best_ratio = 0.0

        for stored_query, answer in candidates:
            ratio = SequenceMatcher(None, query_lower, stored_query.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best = (answer, ratio)

        if best and best_ratio >= FUZZY_THRESHOLD:
            return best
        return None

    def _l1_get(self, query_hash: str) -> Optional[str]:
        entry = self._l1.get(query_hash)
        if not entry:
            return None
        if time.time() - entry.timestamp > self._ttl_seconds:
            self._l1_evict(query_hash)
            return None
        self._l1_order.remove(query_hash)
        self._l1_order.append(query_hash)
        return entry.answer

    def _l1_put(self, query_hash: str, answer: str):
        if query_hash in self._l1:
            self._l1_order.remove(query_hash)
        elif len(self._l1) >= L1_MAX_SIZE:
            oldest = self._l1_order.pop(0)
            del self._l1[oldest]
        self._l1[query_hash] = _L1Entry(answer, time.time())
        self._l1_order.append(query_hash)

    def _l1_evict(self, query_hash: str):
        self._l1.pop(query_hash, None)
        if query_hash in self._l1_order:
            self._l1_order.remove(query_hash)

    def _l2_get_exact(self, query_hash: str) -> Optional[str]:
        with sqlite3.connect(str(CACHE_DB), timeout=5.0) as conn:
            row = conn.execute(
                "SELECT answer, created_at FROM answer_cache WHERE query_hash = ?",
                (query_hash,),
            ).fetchone()
            if not row:
                return None
            answer, created_at = row
            if time.time() - created_at > self._ttl_seconds:
                conn.execute(
                    "DELETE FROM answer_cache WHERE query_hash = ?", (query_hash,)
                )
                conn.commit()
                return None
            conn.execute(
                "UPDATE answer_cache SET hit_count = hit_count + 1 WHERE query_hash = ?",
                (query_hash,),
            )
            conn.commit()
            return answer

    def _l2_get_fuzzy(self, query: str) -> Optional[tuple[str, float]]:
        with sqlite3.connect(str(CACHE_DB), timeout=5.0) as conn:
            rows = conn.execute(
                "SELECT query_text, answer FROM answer_cache ORDER BY hit_count DESC LIMIT 100"
            ).fetchall()
        return self._fuzzy_match(query, rows)

    def _l2_put(self, query_hash: str, query: str, answer: str):
        with sqlite3.connect(str(CACHE_DB), timeout=5.0) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO answer_cache (query_hash, query_text, answer, created_at, hit_count)
                   VALUES (?, ?, ?, ?, COALESCE((SELECT hit_count FROM answer_cache WHERE query_hash = ?), 0) + 1)""",
                (query_hash, query, answer, time.time(), query_hash),
            )
            conn.commit()
        self._l2_cleanup()

    def _l2_cleanup(self):
        with sqlite3.connect(str(CACHE_DB), timeout=5.0) as conn:
            count = conn.execute("SELECT COUNT(*) FROM answer_cache").fetchone()[0]
            if count > self._max_entries:
                to_delete = count - self._max_entries
                conn.execute(
                    "DELETE FROM answer_cache WHERE query_hash IN (SELECT query_hash FROM answer_cache ORDER BY created_at ASC LIMIT ?)",
                    (to_delete,),
                )
                conn.commit()

    async def run(self, query: str) -> CacheLayerOutput:
        query_hash = self._hash(query)

        # 1. L1 in-memory
        if answer := self._l1_get(query_hash):
            return CacheLayerOutput(
                cache_status="hit",
                cached_answer=answer,
                cache_tier="L1",
                similarity_score=1.0,
            )

        # 2. L2 SQLite exact
        if answer := self._l2_get_exact(query_hash):
            self._l1_put(query_hash, answer)
            return CacheLayerOutput(
                cache_status="hit",
                cached_answer=answer,
                cache_tier="L2",
                similarity_score=1.0,
            )

        # 3. L2 SQLite fuzzy
        fuzzy = self._l2_get_fuzzy(query)
        if fuzzy:
            answer, ratio = fuzzy
            self._l1_put(query_hash, answer)
            return CacheLayerOutput(
                cache_status="hit",
                cached_answer=answer,
                cache_tier="L2",
                similarity_score=ratio,
            )

        # 4. Miss
        return CacheLayerOutput(
            cache_status="miss",
            cached_answer=None,
            cache_tier="none",
            similarity_score=0.0,
        )

    def store(self, query: str, answer: str):
        query_hash = self._hash(query)
        self._l1_put(query_hash, answer)
        self._l2_put(query_hash, query, answer)
        logger.info("[CacheLayer] Stored answer for query hash: %s...", query_hash[:8])
