"""Store generic: FAISS (vector) + BM25 (lexical) + meta.json (metadata).

Pipeline cố định cho mọi loại RAG:
    query -> retrieve -> prefilter -> rerank -> top chunks -> return

Không dùng: intent detection, synonym expansion, RRF, sentence highlight,
document routing cố định, hardcode ngành.
"""

import asyncio
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import (
    EMBED_DIM,
    FINAL_K,
    PREFILTER_K,
    RERANK_K,
    RESULT_CACHE_MAX,
    RETRIEVE_K,
)
from .embedder import get_embedder
from .reranker import get_reranker
from .schemas import Chunk

log = logging.getLogger("rag.store")

_TOKEN_RE = re.compile(r"[\w\u00C0-\u024F\u1E00-\u1EFF]+", re.UNICODE)

try:
    from underthesea import word_tokenize as _uts_tokenize

    def _tokenize(text: str) -> List[str]:
        return [t.lower() for t in _uts_tokenize(text) if t.strip()]

except ImportError:  # fallback nếu môi trường không có underthesea

    def _tokenize(text: str) -> List[str]:
        return _TOKEN_RE.findall(text.lower())


def _normalize(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores
    mx = float(scores.max())
    if mx <= 0:
        return np.zeros_like(scores)
    return scores / mx


class FaissMetaStore:
    """1 instance = 1 loại RAG (keyword | comment | social).

    Storage trên đĩa: <persist_dir>/faiss.index + <persist_dir>/meta.json
    Metadata mỗi chunk: {business_id, source_id, source_type, chunk_id, chunk_type, text}
    """

    def __init__(self, name: str, persist_dir: Path, weight_vector: float, weight_bm25: float):
        self.name = name
        self.persist_dir = persist_dir
        self.weight_vector = weight_vector
        self.weight_bm25 = weight_bm25

        self.persist_dir.mkdir(parents=True, exist_ok=True)

        import faiss  # local import: tránh load faiss nếu module không được dùng

        self._faiss = faiss
        self._idx = faiss.IndexFlatIP(EMBED_DIM)
        self._records: List[Dict] = []          # song song với hàng trong _idx
        self._corpus_tokens: List[List[str]] = []
        self._bm25 = None
        self._dedupe_keys: set = set()

        self._lock = asyncio.Lock()
        self._result_cache: Dict[Tuple, List[Chunk]] = {}
        self._result_cache_order: List[Tuple] = []

        self._embedder = get_embedder()
        self._reranker = get_reranker()

        self._load()

    # ── persistence ──────────────────────────────────────────────────────

    def _meta_path(self) -> Path:
        return self.persist_dir / "meta.json"

    def _index_path(self) -> Path:
        return self.persist_dir / "faiss.index"

    def _load(self):
        mp, ip = self._meta_path(), self._index_path()
        if not (mp.exists() and ip.exists()):
            return
        try:
            with open(mp, encoding="utf-8") as f:
                data = json.load(f)
            self._records = data.get("records", [])
            self._dedupe_keys = set(data.get("dedupe_keys", []))
            self._corpus_tokens = [_tokenize(r["text"]) for r in self._records]
            self._rebuild_bm25()
            self._idx = self._faiss.read_index(str(ip))
            log.info(f"[{self.name}] loaded {len(self._records)} chunks")
        except Exception as e:
            log.warning(f"[{self.name}] storage hỏng, khởi tạo lại từ rỗng: {e}")
            self._records, self._corpus_tokens = [], []
            self._bm25, self._dedupe_keys = None, set()
            self._idx = self._faiss.IndexFlatIP(EMBED_DIM)

    def _rebuild_bm25(self):
        from rank_bm25 import BM25Okapi

        self._bm25 = BM25Okapi(self._corpus_tokens) if self._corpus_tokens else None

    def _save_sync(self):
        data = {"records": self._records, "dedupe_keys": list(self._dedupe_keys)}
        mp, ip = self._meta_path(), self._index_path()

        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self.persist_dir, delete=False, suffix=".tmp"
        )
        try:
            json.dump(data, tmp, ensure_ascii=False)
            tmp.close()
            os.replace(tmp.name, mp)
        except Exception:
            os.path.exists(tmp.name) and os.unlink(tmp.name)
            raise

        tmp_idx = tempfile.NamedTemporaryFile(dir=self.persist_dir, delete=False, suffix=".tmp")
        try:
            tmp_idx.close()
            self._faiss.write_index(self._idx, tmp_idx.name)
            os.replace(tmp_idx.name, ip)
        except Exception:
            os.path.exists(tmp_idx.name) and os.unlink(tmp_idx.name)
            raise

    async def _save(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_sync)

    # ── write ──────────────────────────────────────────────────────────

    async def add_chunks(self, records: List[Dict], dedupe_key: str) -> str:
        """records: [{text, chunk_type, chunk_id, business_id, source_id, source_type}, ...]"""
        if not records:
            return "skipped"
        if dedupe_key in self._dedupe_keys:
            return "duplicate"

        async with self._lock:
            if dedupe_key in self._dedupe_keys:
                return "duplicate"

            texts = [r["text"] for r in records]
            embs = await self._embedder.encode(texts)
            if embs.shape[0]:
                self._faiss.normalize_L2(embs)
                self._idx.add(embs)

            for r in records:
                self._records.append(r)
                self._corpus_tokens.append(_tokenize(r["text"]))

            self._rebuild_bm25()
            self._dedupe_keys.add(dedupe_key)
            self._result_cache.clear()
            self._result_cache_order.clear()

            await self._save()
            log.info(f"[{self.name}] add {dedupe_key} -> {len(records)} chunk(s)")
            return "ok"

    async def add_precomputed_batch(
        self,
        records: List[Dict],
        vectors: np.ndarray,
        dedupe_key: str,
    ) -> str:
        """Thêm chunk kèm vector đã có sẵn — dùng cho migration (không re-embed)."""
        if not records:
            return "skipped"
        if dedupe_key in self._dedupe_keys:
            return "duplicate"

        async with self._lock:
            if dedupe_key in self._dedupe_keys:
                return "duplicate"

            vecs = np.asarray(vectors, dtype=np.float32)
            if vecs.shape[0]:
                self._faiss.normalize_L2(vecs)
                self._idx.add(vecs)

            for r in records:
                self._records.append(r)
                self._corpus_tokens.append(_tokenize(r["text"]))

            self._rebuild_bm25()
            self._dedupe_keys.add(dedupe_key)
            self._result_cache.clear()
            self._result_cache_order.clear()

            await self._save()
            return "ok"

    # ── retrieve ─────────────────────────────────────────────────────────

    async def _vector_candidates(self, query: str, k: int) -> Dict[int, float]:
        if not self._idx.ntotal:
            return {}
        emb = await self._embedder.encode([query])
        self._faiss.normalize_L2(emb)
        scores, ids = self._idx.search(emb, min(k, self._idx.ntotal))
        return {int(i): float(s) for s, i in zip(scores[0], ids[0]) if i >= 0 and s > 0}

    def _bm25_candidates(self, query: str, k: int) -> Dict[int, float]:
        if not self._bm25:
            return {}
        scores = np.asarray(self._bm25.get_scores(_tokenize(query)), dtype=np.float32)
        if not scores.size:
            return {}
        top = np.argsort(scores)[::-1][:k]
        return {int(i): float(scores[i]) for i in top if scores[i] > 0}

    def _match_business(self, idx: int, business_id: Optional[str]) -> bool:
        if business_id is None:
            return True
        return self._records[idx].get("business_id") == business_id

    async def retrieve(self, query: str, business_id: Optional[str], k: int) -> List[Chunk]:
        """Hybrid weighted fusion (KHÔNG dùng RRF): score = w_vec*vec + w_bm25*bm25."""
        fetch_k = k * 5 if business_id else k  # over-fetch để bù phần bị lọc theo business_id

        vec_raw = await self._vector_candidates(query, fetch_k)
        bm25_raw = self._bm25_candidates(query, fetch_k)

        vec_vals = _normalize(np.array(list(vec_raw.values()), dtype=np.float32)) if vec_raw else np.array([])
        vec_norm = dict(zip(vec_raw.keys(), vec_vals.tolist()))

        bm25_vals = _normalize(np.array(list(bm25_raw.values()), dtype=np.float32)) if bm25_raw else np.array([])
        bm25_norm = dict(zip(bm25_raw.keys(), bm25_vals.tolist()))

        fused: List[Tuple[float, int]] = []
        for i in set(vec_norm) | set(bm25_norm):
            if not self._match_business(i, business_id):
                continue
            score = self.weight_vector * vec_norm.get(i, 0.0) + self.weight_bm25 * bm25_norm.get(i, 0.0)
            if score > 0:
                fused.append((score, i))

        fused.sort(key=lambda x: x[0], reverse=True)
        fused = fused[:k]
        return [Chunk(text=self._records[i]["text"], meta=self._records[i], score=s) for s, i in fused]

    @staticmethod
    def prefilter(candidates: List[Chunk], k: int) -> List[Chunk]:
        """Rẻ, không model: cắt theo score đã fuse + loại trùng text."""
        seen: set = set()
        out: List[Chunk] = []
        for c in candidates:
            if c.text in seen:
                continue
            seen.add(c.text)
            out.append(c)
            if len(out) >= k:
                break
        return out

    async def rerank(self, query: str, candidates: List[Chunk], k: int) -> List[Chunk]:
        """Chỉ rerank tập đã prefilter (nhỏ) — không rerank toàn bộ retrieve."""
        if not candidates:
            return []
        pairs = [(c.meta.get("chunk_id", c.text[:32]), c.text) for c in candidates]
        scores = await self._reranker.arerank(query, pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [Chunk(text=c.text, meta=c.meta, score=float(s)) for c, s in ranked[:k]]

    # ── result cache ─────────────────────────────────────────────────────

    def _cache_key(self, query: str, business_id: Optional[str], top_k: int) -> Tuple:
        return (query.strip().lower(), business_id, top_k)

    def _cache_get(self, key) -> Optional[List[Chunk]]:
        return self._result_cache.get(key)

    def _cache_put(self, key, value: List[Chunk]):
        if len(self._result_cache) >= RESULT_CACHE_MAX:
            old = self._result_cache_order.pop(0)
            self._result_cache.pop(old, None)
        self._result_cache[key] = value
        self._result_cache_order.append(key)

    
    # ── pipeline: retrieve -> prefilter -> rerank -> final ────────────────

    async def search(
        self,
        query: str,
        business_id: Optional[str] = None,
        top_k: int = FINAL_K,
    ) -> List[Chunk]:
        query = (query or "").strip()
        if not query:
            return []

        key = self._cache_key(query, business_id, top_k)
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        retrieved = await self.retrieve(query, business_id, RETRIEVE_K)
        if not retrieved:
            return []

        prefiltered = self.prefilter(retrieved, PREFILTER_K)
        reranked = await self.rerank(query, prefiltered, RERANK_K)
        final = reranked[: min(top_k, FINAL_K)]

        self._cache_put(key, final)
        return final

    def stats(self) -> dict:
        return {
            "chunks": len(self._records),
            "faiss_vectors": self._idx.ntotal,
            "documents": len(self._dedupe_keys),
        }

    def list_all(
        self,
        business_id: Optional[str] = None,
        chunk_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Liệt kê record thô — không search/rerank, không đụng model."""
        items = self._records
        if business_id:
            items = [r for r in items if r.get("business_id") == business_id]
        if chunk_type:
            items = [r for r in items if r.get("chunk_type") == chunk_type]
        total = len(items)
        return {"total": total, "items": items[offset : offset + limit]}