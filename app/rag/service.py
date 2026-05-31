"""RAG ZERO v3.1 — BGE-M3 + bge-reranker-v2-m3, SOTA multilingual RAG."""

import asyncio
import hashlib
import logging
import os
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import faiss
import json
import numpy as np
import yaml
import torch
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.rag.schemas import Chunk, Doc, Result

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rag")

# ── Config ────────────────────────────────────────────────────────────────────

PERSIST_DIR = Path("./rag_storage")
EMBED_MODEL = "BAAI/bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
DIM = 1024
CHUNK_SIZE = 100
CHUNK_OVERLAP = 15
RRF_K = 10
RRF_GAP = 0.6
BM25_MIN_RATIO = 0.3
L1_MAX = 1000
RERANK_BATCH = 8
RETRIEVE_K = 20
FINAL_K = 3

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32

log.info(f"[config] device={DEVICE} dtype={DTYPE}")

# ── Intent Patterns ───────────────────────────────────────────────────────────

_INTENT_PATTERNS = {
    "entity": re.compile(
        r"là\s+ai|tên\s+là|mật\s+danh|mã\s+(?:nội\s+bộ|xác\s+thực|dự\s+án)|"
        r"giám\s+đốc|trưởng\s+phòng|ceo|cto|cfo|ai\s+là",
        re.IGNORECASE,
    ),
    "numeric": re.compile(
        r"bao\s+nhiêu|mấy|số\s+lượng|ngân\s+sách|giá\s+trị|"
        r"\d+|tỷ|triệu|nghìn|đồng",
        re.IGNORECASE,
    ),
    "purpose": re.compile(
        r"dùng\s+để|mục\s+đích|chức\s+năng|công\s+dụng|"
        r"để\s+làm\s+gì|có\s+tác\s+dụng\s+gì",
        re.IGNORECASE,
    ),
    "location": re.compile(
        r"ở\s+đâu|tại|đặt\s+tại|trụ\s+sở|vị\s+trí|"
        r"thành\s+phố|tỉnh|quận|huyện",
        re.IGNORECASE,
    ),
}


def _detect_intent(query: str) -> str:
    for intent, pattern in _INTENT_PATTERNS.items():
        if pattern.search(query):
            return intent
    return "general"


# ── Tokenizer tiếng Việt ──────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"[\w\u00C0-\u024F\u1E00-\u1EFF]+", re.UNICODE)

try:
    from underthesea import word_tokenize as _uts_tokenize
    def _tokenize(text: str) -> List[str]:
        return [t.lower() for t in _uts_tokenize(text) if t.strip()]
    log.info("[tokenizer] underthesea ✓")
except ImportError:
    def _tokenize(text: str) -> List[str]:
        return _TOKEN_RE.findall(text.lower())
    log.info("[tokenizer] fallback regex")


# ── Synonyms ──────────────────────────────────────────────────────────────────

def _load_synonyms() -> Dict[str, str]:
    path = Path(__file__).parent / "synonyms.yml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    synonym_map = {}
    for group in data.get("bidirectional", []):
        if not group or not isinstance(group, list):
            continue
        canonical = group[0].lower().strip()
        for word in group:
            w = word.lower().strip()
            if w:
                synonym_map[w] = canonical
    return synonym_map

SYNONYMS = _load_synonyms()


def _no_accent(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def expand_query(text: str) -> List[str]:
    result = text.lower()
    for variant, canonical in SYNONYMS.items():
        result = re.sub(r'\b' + re.escape(variant) + r'\b', canonical, result, flags=re.IGNORECASE)
    variants = {text, result, _no_accent(result)}
    intent = _detect_intent(text)
    if intent == "entity":
        stripped = re.sub(r"là\s+ai\??$", "", text.strip(), flags=re.I).strip()
        if stripped and stripped != text.strip():
            variants.update([stripped, _no_accent(stripped)])
    if len(text.split()) <= 4:
        clean = re.sub(r"(là\s+gì|là\s+ai|bao\s+nhiêu|ở\s+đâu|như\s+thế\s+nào)\??$", "", text, flags=re.I).strip()
        if clean and clean != text:
            variants.update([clean, _no_accent(clean)])
    return list(variants)


# ── Async embed helper ────────────────────────────────────────────────────────

async def _aembed(embed_model: SentenceTransformer, texts: List[str]) -> np.ndarray:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, lambda: embed_model.encode(texts, normalize_embeddings=True)
    )


# ── Reranker (lazy-load) ──────────────────────────────────────────────────────

# [PATCH 1] Lazy-load: không load model lúc startup, chỉ load khi gọi lần đầu.
# Tránh block main thread và tránh load model nếu chưa cần.

class Reranker:
    def __init__(self):
        self._tokenizer = None
        self._model = None
        self._lock = asyncio.Lock()

    def _load(self):
        if self._model is not None:
            return
        log.info(f"[reranker] loading {RERANK_MODEL}...")
        self._tokenizer = AutoTokenizer.from_pretrained(RERANK_MODEL, trust_remote_code=True)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            RERANK_MODEL, torch_dtype=DTYPE, trust_remote_code=True,
        ).to(DEVICE).eval()
        log.info(f"[reranker] loaded on {DEVICE}")

    @torch.no_grad()
    def rerank(self, query: str, chunks: List[Chunk], batch_size: int = RERANK_BATCH) -> List[Tuple[Chunk, float]]:
        if not chunks:
            return []
        self._load()
        pairs = [[query, c.text] for c in chunks]
        scores = []
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i + batch_size]
            inputs = self._tokenizer(batch, padding=True, truncation=True, return_tensors="pt", max_length=512)
            if DEVICE == "cuda":
                inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
            out = self._model(**inputs).logits.view(-1)
            if DTYPE == torch.float16:
                out = out.float()
            scores.extend(torch.sigmoid(out).cpu().tolist())
        return sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)

    async def arerank(self, query: str, chunks: List[Chunk]) -> List[Tuple[Chunk, float]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.rerank, query, chunks)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _vec(emb) -> np.ndarray:
    v = np.array([emb], dtype=np.float32)
    faiss.normalize_L2(v)
    return v


def _rrf(lists: List[List[Chunk]], k: int = RRF_K, weights: Optional[List[float]] = None) -> List[Chunk]:
    ranks: Dict[str, Dict] = {}
    n_lists = len(lists)
    weights = weights or [1.0] * n_lists
    for list_idx, lst in enumerate(lists):
        w = weights[list_idx]
        for rank, c in enumerate(lst):
            key = hashlib.md5(c.text.encode()).hexdigest()
            if key not in ranks:
                ranks[key] = {"chunk": c, "score": 0.0, "lists": set()}
            ranks[key]["score"] += w / (k + rank + 1)
            ranks[key]["lists"].add(list_idx)
    sorted_items = sorted(ranks.values(), key=lambda x: x["score"], reverse=True)
    if not sorted_items:
        return []
    winner_score = sorted_items[0]["score"]
    # [PATCH 2] Fix RRF filter: chỉ dùng score threshold, bỏ điều kiện len(lists) gây giữ chunk kém.
    return [
        Chunk(score=v["score"], text=v["chunk"].text, meta=v["chunk"].meta)
        for v in sorted_items
        if v["score"] >= winner_score * RRF_GAP
    ]


# ── Sentence Highlight ────────────────────────────────────────────────────────

def _keyword_overlap(query: str, text: str) -> float:
    q_tokens = set(t for t in _tokenize(query) if len(t) > 2)
    t_tokens = set(t for t in _tokenize(text) if len(t) > 2)
    if not q_tokens:
        return 0.0
    return len(q_tokens & t_tokens) / len(q_tokens)


def _highlight_sentence(chunk: Chunk, query: str) -> Chunk:
    text = chunk.text.strip() if chunk.text else ""
    if not text or len(text) < 20:
        return chunk
    overlap = _keyword_overlap(query, text)
    if len(text) < 80 or overlap >= 0.5:
        return chunk
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) <= 1:
        return chunk
    query_tokens = set(t for t in _tokenize(query) if len(t) > 2)
    best_sent, best_score = sentences[0], 0
    for sent in sentences:
        score = len(query_tokens & set(t for t in _tokenize(sent) if len(t) > 2))
        if score > best_score:
            best_score, best_sent = score, sent
    if best_score > 0 and _keyword_overlap(query, best_sent) > overlap:
        sent_overlap = _keyword_overlap(query, best_sent)
        return Chunk(
            score=chunk.score * (0.7 + 0.3 * min(sent_overlap, 1.0)),
            text=best_sent.strip(),
            meta={**chunk.meta, "highlighted": True, "full_chunk": chunk.text},
        )
    return chunk


# ── Cache ─────────────────────────────────────────────────────────────────────

# [PATCH 3] Cache lưu List[Chunk] thay vì Chunk đơn lẻ, consistent với Result.

class Cache:
    def __init__(self):
        self._l1: Dict[str, List[Chunk]] = {}

    def get(self, q: str) -> Optional[List[Chunk]]:
        return self._l1.get(q.lower().strip())

    def put(self, q: str, chunks: List[Chunk]):
        if len(self._l1) >= L1_MAX:
            del self._l1[next(iter(self._l1))]
        self._l1[q.lower().strip()] = chunks

    def stats(self) -> dict:
        return {"l1": len(self._l1)}


# ── Store ─────────────────────────────────────────────────────────────────────

class Store:
    def __init__(self, embed: SentenceTransformer):
        self._embed = embed
        self._idx = faiss.IndexFlatIP(DIM)
        self._texts: List[str] = []
        self._metas: List[dict] = []
        self._bm25_corpus: List[List[str]] = []
        self._bm25: Optional[BM25Okapi] = None
        self._hashes: Set[str] = set()
        # [PATCH 4] Lock để tránh concurrent add() corrupt BM25 + file save.
        self._lock = asyncio.Lock()
        PERSIST_DIR.mkdir(exist_ok=True)
        self._load()

    async def add(self, doc: Doc) -> str:
        text = doc.text.strip()
        if not text:
            return "skipped"
        h = hashlib.sha256(text.encode()).hexdigest()[:16]
        if h in self._hashes:
            return "duplicate"

        async with self._lock:
            # double-check sau khi acquire lock
            if h in self._hashes:
                return "duplicate"

            chunks = self._chunk(text)
            meta = {"source_id": doc.metadata.get("source_id", h), **doc.metadata}

            embs_list = await _aembed(self._embed, chunks)
            embs = np.array(embs_list, dtype=np.float32)
            faiss.normalize_L2(embs)
            self._idx.add(embs)

            for i, c in enumerate(chunks):
                self._texts.append(c)
                self._metas.append({**meta, "chunk_idx": i})
                self._bm25_corpus.append(_tokenize(c))

            self._bm25 = BM25Okapi(self._bm25_corpus)
            self._hashes.add(h)
            self._save()
            log.info(f"[add] {h} → {len(chunks)} chunk(s)")
            return "ok"

    def _chunk(self, text: str) -> List[str]:
        # [PATCH 5] Implement CHUNK_OVERLAP: mỗi chunk mới bắt đầu lại từ
        # (CHUNK_SIZE - CHUNK_OVERLAP) words trước đó để giữ context liên tục.
        paragraphs = [p.strip() for p in re.split(r"\n\n+|\n(?=\d+\.\s)", text) if p.strip()]
        chunks = []
        for para in paragraphs:
            words = para.split()
            if len(words) <= CHUNK_SIZE:
                chunks.append(para)
                continue
            sentences = re.split(r"(?<=[.!?])\s+", para)
            current: List[str] = []
            current_len = 0
            for sent in sentences:
                sent_words = sent.split()
                if current_len + len(sent_words) <= CHUNK_SIZE:
                    current.append(sent)
                    current_len += len(sent_words)
                else:
                    if current:
                        chunks.append(" ".join(current))
                        # overlap: giữ lại các sentence cuối cho đến khi tổng words <= CHUNK_OVERLAP
                        overlap_sents: List[str] = []
                        overlap_len = 0
                        for s in reversed(current):
                            wl = len(s.split())
                            if overlap_len + wl > CHUNK_OVERLAP:
                                break
                            overlap_sents.insert(0, s)
                            overlap_len += wl
                        current = overlap_sents
                        current_len = overlap_len
                    current.append(sent)
                    current_len += len(sent_words)
            if current:
                chunks.append(" ".join(current))
        return chunks

    async def vector(self, query: str, k: int) -> List[Chunk]:
        if not self._idx.ntotal:
            return []
        emb = await _aembed(self._embed, [query])
        v = _vec(emb[0])
        scores, ids = self._idx.search(v, k)
        return [
            Chunk(float(s), self._texts[i], self._metas[i])
            for s, i in zip(scores[0], ids[0])
            if i >= 0 and s > 0
        ]

    def bm25(self, queries: List[str], k: int) -> List[Chunk]:
        if not self._bm25:
            return []
        tokenized = [_tokenize(q) for q in queries]
        raw = np.max([self._bm25.get_scores(t) for t in tokenized], axis=0)
        top = np.argsort(raw)[::-1][:k]
        if not len(top):
            return []
        mx = raw.max() or 1.0
        best = raw[top[0]]
        return [
            Chunk(float(raw[i] / mx), self._texts[i], self._metas[i])
            for i in top
            if raw[i] > 0 and raw[i] >= best * BM25_MIN_RATIO
        ]

    def stats(self) -> dict:
        return {"chunks": len(self._texts), "hashes": len(self._hashes), "faiss_vectors": self._idx.ntotal}

    def _save(self):
        data = {"texts": self._texts, "metas": self._metas, "corpus": self._bm25_corpus, "hashes": list(self._hashes)}
        json_path = PERSIST_DIR / "data.json"
        tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=PERSIST_DIR, delete=False, suffix=".tmp")
        try:
            json.dump(data, tmp, ensure_ascii=False)
            tmp.close()
            os.replace(tmp.name, json_path)
        except Exception:
            os.unlink(tmp.name)
            raise
        idx_path = PERSIST_DIR / "faiss.index"
        tmp_idx = tempfile.NamedTemporaryFile(dir=PERSIST_DIR, delete=False, suffix=".tmp")
        try:
            tmp_idx.close()
            faiss.write_index(self._idx, tmp_idx.name)
            os.replace(tmp_idx.name, idx_path)
        except Exception:
            os.path.exists(tmp_idx.name) and os.unlink(tmp_idx.name)
            raise

    def _load(self):
        dp, fp = PERSIST_DIR / "data.json", PERSIST_DIR / "faiss.index"
        if not (dp.exists() and fp.exists()):
            return
        try:
            with open(dp, encoding="utf-8") as f:
                d = json.load(f)
            self._texts = d["texts"]
            self._metas = d["metas"]
            self._bm25_corpus = d["corpus"]
            self._bm25 = BM25Okapi(self._bm25_corpus) if self._bm25_corpus else None
            self._hashes = set(d["hashes"])
            self._idx = faiss.read_index(str(fp))
            log.info(f"[load] {len(self._texts)} chunks restored")
        except Exception as e:
            log.warning(f"[load] corrupt files, starting fresh: {e}")
            self._texts, self._metas, self._bm25_corpus = [], [], []
            self._bm25, self._hashes = None, set()
            self._idx = faiss.IndexFlatIP(DIM)


# ── RAG Pipeline ──────────────────────────────────────────────────────────────

class RAG:
    def __init__(self):
        self._embed = SentenceTransformer(EMBED_MODEL)
        self._reranker = Reranker()          # lazy: không load model ở đây
        self._store = Store(self._embed)
        self._cache = Cache()

    async def add(self, text: str, **meta) -> str:
        return await self._store.add(Doc(text, meta))

    async def search(self, query: str, top_k: int = FINAL_K) -> Result:
        query = query.strip()
        intent = _detect_intent(query)

        # L1 exact cache
        if cached := self._cache.get(query):
            return Result(query, cached, "cache_l1")

        # Step 1: Retrieve
        variants = expand_query(query)
        bm25_hits = self._store.bm25(variants, RETRIEVE_K)
        vec_hits = await self._store.vector(variants[0], RETRIEVE_K)

        weights = (
            [0.7, 1.3] if intent in ("purpose", "general") else
            [1.3, 0.7] if intent in ("entity", "numeric") else
            [1.0, 1.0]
        )
        fused = _rrf([bm25_hits, vec_hits], weights=weights)[:RETRIEVE_K]

        if not fused:
            return Result(query, [], "no_match")

        # Step 2: Rerank
        reranked = await self._reranker.arerank(query, fused)
        if not reranked or reranked[0][1] < 0.05:
            return Result(query, [], "no_match")
        top_chunks = [c for c, _ in reranked[:top_k]]

        # Step 3: Highlight
        highlighted = [_highlight_sentence(c, query) for c in top_chunks]

        if reranked:
            log.info(f"[search] intent={intent} rerank_top={round(reranked[0][1], 4)} "
                     f"retrieve={len(fused)} final={len(highlighted)}")

        self._cache.put(query, highlighted)
        return Result(query, highlighted, f"reranked_{intent}")

    def stats(self) -> dict:
        return {
            "store": self._store.stats(),
            "cache": self._cache.stats(),
            "embed_model": EMBED_MODEL,
            "rerank_model": RERANK_MODEL,
            "device": DEVICE,
        }