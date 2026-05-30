"""RAG ZERO v2.1 — compact single-file RAG with BM25 + FAISS + RRF fusion."""

import asyncio, hashlib, logging, unicodedata, tempfile, os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import json
import faiss
import numpy as np
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rag")

PERSIST_DIR    = Path("./rag_storage")
EMBED_MODEL    = "BAAI/bge-small-en-v1.5"
DIM            = 384
CHUNK_SIZE     = 512
CHUNK_OVERLAP  = 50
RRF_K          = 60
RRF_GAP        = 0.6
BM25_MIN_RATIO = 0.3
L2_THRESHOLD   = 0.85
L1_MAX         = 1000


# ── Async embed helper ────────────────────────────────────────────────────────

async def _aembed(embed_model: TextEmbedding, text: str) -> np.ndarray:
    """
    fastembed.TextEmbedding chỉ có embed() đồng bộ (sync).
    Bọc trong run_in_executor để không block event loop.
    embed() trả về generator → list()[0] để lấy vector.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: list(embed_model.embed([text]))[0]
    )


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Doc:
    text: str
    metadata: dict = field(default_factory=dict)

@dataclass
class Chunk:
    score: float
    text:  str
    meta:  dict

@dataclass
class Result:
    query:  str
    chunks: List[Chunk]
    source: str


# ── Synonyms ──────────────────────────────────────────────────────────────────

SYNONYMS = {
    "thưởng tháng 13": ["tiền thưởng cuối năm", "bonus tết", "lương tháng 13", "thưởng tết"],
    "nghỉ phép năm":   ["annual leave", "phép năm", "ngày phép hưởng lương"],
    "nghỉ phép":       ["ngày phép", "leave", "day off", "xin nghỉ"],
    "public code":     ["public mã nguồn", "đăng github", "upload source", "chia sẻ code"],
    "lương":           ["tiền công", "thu nhập"],
    "bảo mật":         ["security", "an ninh", "confidential"],
}

_reverse = {v.lower(): k for k, vs in SYNONYMS.items() for v in vs}
_reverse.update({k.lower(): k for k in SYNONYMS})
_reverse = dict(sorted(_reverse.items(), key=lambda x: len(x[0]), reverse=True))

def _no_accent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def expand_query(text: str) -> List[str]:
    result = text.lower()
    for variant, canonical in _reverse.items():
        if variant in result and variant != canonical:
            result = result.replace(variant, canonical)
    variants = list({text, result, _no_accent(result)})
    return variants


# ── Cache (L1 exact + L2 semantic) ───────────────────────────────────────────

class Cache:
    def __init__(self, embed: TextEmbedding):
        self._l1: Dict[str, Chunk] = {}
        self._embed = embed
        self._idx   = faiss.IndexFlatIP(DIM)
        self._items: List[Chunk] = []

    def get_l1(self, q: str) -> Optional[Chunk]:
        return self._l1.get(q.lower().strip())

    def put_l1(self, q: str, c: Chunk):
        if len(self._l1) >= L1_MAX:
            del self._l1[next(iter(self._l1))]
        self._l1[q.lower().strip()] = c

    async def get_l2(self, q: str) -> Optional[Chunk]:
        if not self._idx.ntotal:
            return None
        v = _vec(await _aembed(self._embed, q))  # ← fixed
        scores, ids = self._idx.search(v, 1)
        return self._items[ids[0][0]] if scores[0][0] >= L2_THRESHOLD else None

    async def put_l2(self, q: str, c: Chunk):
        self._idx.add(_vec(await _aembed(self._embed, q)))  # ← fixed
        self._items.append(c)

    def stats(self): return {"l1": len(self._l1), "l2": self._idx.ntotal}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _vec(emb) -> np.ndarray:
    v = np.array([emb], dtype=np.float32)
    faiss.normalize_L2(v)
    return v

def _key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]

def _rrf(lists: List[List[Chunk]], k: int = RRF_K) -> List[Chunk]:
    ranks: Dict[int, Dict] = {}
    for list_idx, lst in enumerate(lists):
        for rank, c in enumerate(lst):
            key = hash(c.text)
            if key not in ranks:
                ranks[key] = {"chunk": c, "score": 0.0, "lists": set()}
            ranks[key]["score"] += 1.0 / (k + rank + 1)
            ranks[key]["lists"].add(list_idx)
    sorted_items = sorted(ranks.values(), key=lambda x: x["score"], reverse=True)
    if not sorted_items:
        return []
    winner_score = sorted_items[0]["score"]
    n_lists = len(lists)
    return [
        Chunk(score=v["score"], text=v["chunk"].text, meta=v["chunk"].meta)
        for v in sorted_items
        if v["score"] >= winner_score * RRF_GAP or len(v["lists"]) >= n_lists
    ]


# ── Store (ingest + search) ───────────────────────────────────────────────────

class Store:
    def __init__(self, embed: TextEmbedding):
        self._embed  = embed
        self._idx    = faiss.IndexFlatIP(DIM)
        self._texts: List[str]       = []
        self._metas: List[dict]      = []
        self._bm25_corpus: List[List[str]] = []
        self._bm25: Optional[BM25Okapi]    = None
        self._hashes: Set[str]             = set()
        PERSIST_DIR.mkdir(exist_ok=True)
        self._load()

    # ── Ingest ────────────────────────────────────────────────────────────────

    async def add(self, doc: Doc) -> str:
        text = doc.text.strip()
        h    = hashlib.sha256(text.encode()).hexdigest()[:16]
        if not text or h in self._hashes:
            return "duplicate" if text else "skipped"

        chunks = self._chunk(text)
        meta   = {"source_id": doc.metadata.get("source_id", h), **doc.metadata}

        # PARALLEL EMBEDDING: gather các coroutine _aembed concurrently
        embs_list = await asyncio.gather(*[_aembed(self._embed, c) for c in chunks])  # ← fixed
        embs = np.array(embs_list, dtype=np.float32)
        faiss.normalize_L2(embs)
        self._idx.add(embs)

        for i, c in enumerate(chunks):
            self._texts.append(c)
            self._metas.append({**meta, "chunk_idx": i})
            self._bm25_corpus.append(c.lower().split())

        self._bm25 = BM25Okapi(self._bm25_corpus)
        self._hashes.add(h)
        self._save()
        log.info(f"[add] {h} → {len(chunks)} chunk(s)")
        return "ok"

    def _chunk(self, text: str) -> List[str]:
        words = text.split()
        if len(words) <= CHUNK_SIZE:
            return [text]
        out, start = [], 0
        while start < len(words):
            out.append(" ".join(words[start:start + CHUNK_SIZE]))
            start += CHUNK_SIZE - CHUNK_OVERLAP
        return out

    # ── Search ────────────────────────────────────────────────────────────────

    async def vector(self, query: str, k: int) -> List[Chunk]:
        if not self._idx.ntotal:
            return []
        scores, ids = self._idx.search(_vec(await _aembed(self._embed, query)), k)  # ← fixed
        return [
            Chunk(float(s), self._texts[i], self._metas[i])
            for s, i in zip(scores[0], ids[0]) if i >= 0 and s > 0
        ]

    def bm25(self, queries: List[str], k: int) -> List[Chunk]:
        if not self._bm25:
            return []
        raw = np.max(
            [self._bm25.get_scores(q.lower().split()) for q in queries], axis=0
        )
        top  = np.argsort(raw)[::-1][:k]
        mx   = raw.max() or 1
        best = raw[top[0]] if len(top) else 1
        return [
            Chunk(float(raw[i] / mx), self._texts[i], self._metas[i])
            for i in top if raw[i] > 0 and raw[i] >= best * BM25_MIN_RATIO
        ]

    # ── Persist ───────────────────────────────────────────────────────────────

    def _save(self):
        """Atomic write: ghi ra temp rồi rename, tránh corrupted file nếu crash giữa chừng."""
        data = {
            "texts":  self._texts,
            "metas":  self._metas,
            "corpus": self._bm25_corpus,
            "hashes": list(self._hashes),
        }
        json_path = PERSIST_DIR / "data.json"
        tmp_json = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=PERSIST_DIR, delete=False, suffix=".tmp"
        )
        try:
            json.dump(data, tmp_json, ensure_ascii=False)
            tmp_json.close()
            os.replace(tmp_json.name, json_path)
        except Exception:
            os.unlink(tmp_json.name)
            raise

        index_path = PERSIST_DIR / "faiss.index"
        tmp_index = tempfile.NamedTemporaryFile(dir=PERSIST_DIR, delete=False, suffix=".tmp")
        try:
            tmp_index.close()
            faiss.write_index(self._idx, tmp_index.name)
            os.replace(tmp_index.name, index_path)
        except Exception:
            if os.path.exists(tmp_index.name):
                os.unlink(tmp_index.name)
            raise

    def _load(self):
        """Graceful degradation: nếu file hỏng, log warning và khởi động store rỗng."""
        dp, fp = PERSIST_DIR / "data.json", PERSIST_DIR / "faiss.index"
        if not (dp.exists() and fp.exists()):
            return
        try:
            with open(dp, "r", encoding="utf-8") as f:
                d = json.load(f)
            self._texts, self._metas = d["texts"], d["metas"]
            self._bm25_corpus = d["corpus"]
            self._bm25 = BM25Okapi(self._bm25_corpus) if self._bm25_corpus else None
            self._hashes = set(d["hashes"])
            self._idx = faiss.read_index(str(fp))
            log.info(f"[load] {len(self._texts)} chunks restored")
        except Exception as e:
            log.warning(f"[load] Corrupted persist files, starting fresh: {e}")
            self._texts, self._metas, self._bm25_corpus = [], [], []
            self._bm25, self._hashes = None, set()
            self._idx = faiss.IndexFlatIP(DIM)


# ── RAG Pipeline ──────────────────────────────────────────────────────────────

class RAG:
    def __init__(self):
        self._embed = TextEmbedding(model_name=EMBED_MODEL)
        self._store = Store(self._embed)
        self._cache = Cache(self._embed)

    async def add(self, text: str, **meta) -> str:
        return await self._store.add(Doc(text, meta))

    async def search(self, query: str, top_k: int = 3) -> Result:
        query = query.strip()

        if c := self._cache.get_l1(query):
            return Result(query, [c], "cache_l1")
        if c := await self._cache.get_l2(query):
            return Result(query, [c], "cache_l2")

        variants  = expand_query(query)
        bm25_hits = self._store.bm25(variants, top_k * 3)
        vec_hits  = await self._store.vector(variants[0], top_k * 3)
        fused     = _rrf([bm25_hits, vec_hits])[:top_k]

        log.info(
            f"[search] bm25={len(bm25_hits)} vec={len(vec_hits)} "
            f"fused_top3: {[(round(c.score,4), c.meta.get('source_id','?')) for c in fused[:3]]}"
        )

        if not fused:
            return Result(query, [], "no_match")

        self._cache.put_l1(query, fused[0])
        await self._cache.put_l2(query, fused[0])
        return Result(query, fused, "fusion")