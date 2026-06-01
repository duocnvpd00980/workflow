"""RAG ZERO v2.5.1 — BM25 + FAISS hybrid, sentence highlight, cloud-optimized.

Fixes from v2.5:
- Fix _highlight_sentence empty/short text bug causing low_confidence false positives
- Add intent-keyword mismatch guard (purpose vs location)
- Add empty text guard in highlight
- Better logging for debug
"""

import asyncio
import hashlib
import logging
import os
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Set

import faiss
import json
import numpy as np
import yaml
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi

from app.rag.schemas import Chunk, Doc, Result

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rag")

# ── Config ────────────────────────────────────────────────────────────────────

PERSIST_DIR = Path("./rag_storage")
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM = 384
CHUNK_SIZE = 50
CHUNK_OVERLAP = 8
RRF_K = 10
RRF_GAP = 0.6
BM25_MIN_RATIO = 0.3
L1_MAX = 1000

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


# ── Tokenizer tiếng Việt ───────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"[\w\u00C0-\u024F\u1E00-\u1EFF]+", re.UNICODE)

try:
    from underthesea import word_tokenize as _uts_tokenize
    def _tokenize(text: str) -> List[str]:
        return [t.lower() for t in _uts_tokenize(text) if t.strip()]
    log.info("[tokenizer] underthesea ✓")
except ImportError:
    def _tokenize(text: str) -> List[str]:
        return _TOKEN_RE.findall(text.lower())
    log.info("[tokenizer] fallback regex (cài underthesea để tốt hơn: pip install underthesea)")


# ── Synonyms (Bidirectional) ──────────────────────────────────────────────────

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
        result = re.sub(
            r'\b' + re.escape(variant) + r'\b',
            canonical,
            result,
            flags=re.IGNORECASE
        )
    variants = {text, result, _no_accent(result)}
    intent = _detect_intent(text)
    if intent == "entity":
        stripped = re.sub(r"là\s+ai\??$", "", text.strip(), flags=re.I).strip()
        if stripped and stripped != text.strip():
            variants.add(stripped)
    return list(variants)


# ── Async embed helper ────────────────────────────────────────────────────────

async def _aembed(embed_model: TextEmbedding, text: str) -> np.ndarray:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, lambda: list(embed_model.embed([text]))[0]
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _vec(emb) -> np.ndarray:
    v = np.array([emb], dtype=np.float32)
    faiss.normalize_L2(v)
    return v


def _is_content_chunk(text: str) -> bool:
    """Check if chunk has actual content vs just section header."""
    text = text.strip()
    # Section header: short, starts with number, mostly uppercase
    if re.match(r"^\d+\.\s+[A-Z]", text) and len(text) < 50:
        return False
    # Very short chunks are likely headers
    if len(text) < 30:
        return False
    return True


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
            # Boost content chunks, penalize section headers
            content_boost = 1.2 if _is_content_chunk(c.text) else 0.8
            ranks[key]["score"] += w * content_boost / (k + rank + 1)
            ranks[key]["lists"].add(list_idx)

    sorted_items = sorted(ranks.values(), key=lambda x: x["score"], reverse=True)
    if not sorted_items:
        return []

    winner_score = sorted_items[0]["score"]
    return [
        Chunk(score=v["score"], text=v["chunk"].text, meta=v["chunk"].meta)
        for v in sorted_items
        if v["score"] >= winner_score * RRF_GAP or len(v["lists"]) >= n_lists
    ]


# ── Sentence Highlight ────────────────────────────────────────────────────────

def _keyword_overlap(query: str, text: str) -> float:
    """Tỷ lệ keyword overlap giữa query và text."""
    q_tokens = set(t for t in _tokenize(query) if len(t) > 2)
    t_tokens = set(t for t in _tokenize(text) if len(t) > 2)
    if not q_tokens:
        return 0.0
    return len(q_tokens & t_tokens) / len(q_tokens)


def _highlight_sentence(chunk: Chunk, query: str) -> Chunk:
    """Highlight sentence có keyword overlap cao nhất trong chunk.

    Guard: nếu chunk ngắn, rỗng, hoặc đã đủ liên quan → giữ nguyên.
    """
    text = chunk.text.strip() if chunk.text else ""

    # Guard: empty or very short
    if not text or len(text) < 20:
        log.debug(f"[highlight] skip: text too short or empty")
        return chunk

    overlap = _keyword_overlap(query, text)

    # Chunk ngắn hoặc đã đủ liên quan → giữ nguyên
    # But still try to find best sentence for medium chunks
    if len(text) < 80:
        log.debug(f"[highlight] keep short: len={len(text)}")
        return chunk
    if overlap >= 0.5:
        log.debug(f"[highlight] keep good overlap: {overlap:.2f}")
        return chunk

    # Split sentences, filter empty
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) <= 1:
        log.debug(f"[highlight] keep: single sentence")
        return chunk

    best_sent = sentences[0]
    best_score = 0
    query_tokens = set(t for t in _tokenize(query) if len(t) > 2)

    for sent in sentences:
        sent_tokens = set(t for t in _tokenize(sent) if len(t) > 2)
        score = len(query_tokens & sent_tokens)
        if score > best_score:
            best_score = score
            best_sent = sent

    # Chỉ highlight nếu sentence tìm được thực sự tốt hơn
    if best_score > 0:
        sent_overlap = _keyword_overlap(query, best_sent)
        if sent_overlap > overlap:
            log.debug(f"[highlight] highlight: overlap {overlap:.2f} -> {sent_overlap:.2f}")
            return Chunk(
                score=chunk.score * (0.7 + 0.3 * min(sent_overlap, 1.0)),
                text=best_sent.strip(),
                meta={
                    **chunk.meta,
                    "highlighted": True,
                    "full_chunk": chunk.text,
                    "sent_overlap": round(sent_overlap, 3),
                }
            )

    log.debug(f"[highlight] keep: no better sentence found")
    return chunk


# ── Intent Mismatch Guard ─────────────────────────────────────────────────────

_INTENT_KEYWORDS = {
    "purpose": {"dùng", "mục", "đích", "chức", "năng", "công", "dụng", "lưu", "trữ", 
                "xử", "lý", "phân", "tích", "hệ", "thống", "nền", "tảng", "giải", "pháp"},
    "location": {"tại", "ở", "đặt", "trụ", "sở", "thành", "phố", "tỉnh", "quận", "huyện", "đà", "nẵng", "hồ", "chí", "minh"},
    "entity": {"là", "tên", "mã", "mật", "danh", "giám", "đốc", "trưởng", "phòng"},
    "numeric": {"ngân", "sách", "chi", "phí", "kinh", "phí", "bao", "nhiêu", "tỷ", "triệu"},
}


def _check_intent_mismatch(intent: str, text: str) -> bool:
    """Kiểm tra nếu text có keywords phù hợp với intent.
    Trả về True nếu KHÔNG mismatch. Very lenient - only obvious mismatches.
    """
    if intent not in _INTENT_KEYWORDS:
        return True

    tokens = set(t for t in _tokenize(text) if len(t) > 1)

    # Only check: purpose query but result is ONLY location (no function words at all)
    if intent == "purpose":
        intent_kw = _INTENT_KEYWORDS["purpose"]
        location_kw = _INTENT_KEYWORDS["location"]
        has_intent = bool(tokens & intent_kw)
        has_location = bool(tokens & location_kw)
        # Only mismatch if NO intent words AND has location AND is very short
        if not has_intent and has_location and len(text) < 40:
            log.debug(f"[intent_check] purpose vs location mismatch")
            return False

    return True


# ── Cache (L1 exact only) ───────────────────────────────────────────────────

class Cache:
    def __init__(self):
        self._l1: Dict[str, Chunk] = {}

    def get_l1(self, q: str) -> Optional[Chunk]:
        return self._l1.get(q.lower().strip())

    def put_l1(self, q: str, c: Chunk):
        if len(self._l1) >= L1_MAX:
            del self._l1[next(iter(self._l1))]
        self._l1[q.lower().strip()] = c

    def stats(self) -> dict:
        return {"l1": len(self._l1)}


# ── Store (ingest + search) ─────────────────────────────────────────────────

class Store:
    def __init__(self, embed: TextEmbedding):
        self._embed = embed
        self._idx = faiss.IndexFlatIP(DIM)
        self._texts: List[str] = []
        self._metas: List[dict] = []
        self._bm25_corpus: List[List[str]] = []
        self._bm25: Optional[BM25Okapi] = None
        self._hashes: Set[str] = set()
        PERSIST_DIR.mkdir(exist_ok=True)
        self._load()

    async def add(self, doc: Doc) -> str:
        text = doc.text.strip()
        h = hashlib.sha256(text.encode()).hexdigest()[:16]
        if not text:
            return "skipped"
        if h in self._hashes:
            return "duplicate"

        chunks = self._chunk(text)
        meta = {"source_id": doc.metadata.get("source_id", h), **doc.metadata}

        embs_list = await asyncio.gather(*[_aembed(self._embed, c) for c in chunks])
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
        paragraphs = [p.strip() for p in re.split(r"\n\n+|\n(?=\d+\.\s)", text) if p.strip()]
        chunks = []
        for para in paragraphs:
            words = para.split()
            if len(words) <= CHUNK_SIZE:
                chunks.append(para)
                continue
            sentences = re.split(r"(?<=[.!?])\s+", para)
            current = []
            current_len = 0
            for sent in sentences:
                sent_words = sent.split()
                if current_len + len(sent_words) <= CHUNK_SIZE:
                    current.append(sent)
                    current_len += len(sent_words)
                else:
                    if current:
                        chunks.append(" ".join(current))
                    current = [sent]
                    current_len = len(sent_words)
            if current:
                chunks.append(" ".join(current))
        return chunks

    async def vector(self, query: str, k: int) -> List[Chunk]:
        if not self._idx.ntotal:
            return []
        v = _vec(await _aembed(self._embed, query))
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
        raw = np.max(
            [self._bm25.get_scores(tokens) for tokens in tokenized], axis=0
        )
        top = np.argsort(raw)[::-1][:k]
        if len(top) == 0:
            return []
        mx = raw.max() or 1.0
        best = raw[top[0]]
        return [
            Chunk(float(raw[i] / mx), self._texts[i], self._metas[i])
            for i in top
            if raw[i] > 0 and raw[i] >= best * BM25_MIN_RATIO
        ]

    def stats(self) -> dict:
        return {
            "chunks": len(self._texts),
            "hashes": len(self._hashes),
            "faiss_vectors": self._idx.ntotal,
        }

    def _save(self):
        data = {
            "texts": self._texts,
            "metas": self._metas,
            "corpus": self._bm25_corpus,
            "hashes": list(self._hashes),
        }
        json_path = PERSIST_DIR / "data.json"
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=PERSIST_DIR, delete=False, suffix=".tmp"
        )
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
            if os.path.exists(tmp_idx.name):
                os.unlink(tmp_idx.name)
            raise

    def _load(self):
        dp = PERSIST_DIR / "data.json"
        fp = PERSIST_DIR / "faiss.index"
        if not (dp.exists() and fp.exists()):
            return
        try:
            with open(dp, "r", encoding="utf-8") as f:
                d = json.load(f)
            self._texts = d["texts"]
            self._metas = d["metas"]
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
        self._cache = Cache()

    async def add(self, text: str, **meta) -> str:
        return await self._store.add(Doc(text, meta))

    async def search(self, query: str, top_k: int = 3) -> Result:
        query = query.strip()
        intent = _detect_intent(query)

        # L1 exact cache
        if c := self._cache.get_l1(query):
            return Result(query, [c], "cache_l1")

        # Dynamic retrieve count
        retrieve_k = top_k * 5 if intent in ("entity", "numeric") else top_k * 8

        variants = expand_query(query)
        bm25_hits = self._store.bm25(variants, retrieve_k)
        vec_hits = await self._store.vector(variants[0], retrieve_k)

        # Dynamic RRF weights
        if intent in ("purpose", "general"):
            weights = [0.7, 1.3]
        elif intent in ("entity", "numeric"):
            weights = [1.3, 0.7]
        else:
            weights = [1.0, 1.0]

        fused = _rrf([bm25_hits, vec_hits], weights=weights)[:top_k]

        if not fused:
            return Result(query, [], "no_match")

        # Post-processing: highlight best sentence trong mỗi chunk
        highlighted = []
        for chunk in fused:
            h_chunk = _highlight_sentence(chunk, query)
            highlighted.append(h_chunk)

        # Post-filter: for purpose queries, reject if top result is only a section header
        if intent == "purpose" and highlighted:
            top_text = highlighted[0].text.strip()
            # Section header pattern: "2. HỆ THỐNG CƠ SỞ" or very short
            is_header = re.match(r"^\d+\.\s+[A-Z]", top_text) or len(top_text) < 30
            # Check if has actual content words (verbs, function descriptions)
            has_content = bool(re.search(r"(đào tạo|lưu trữ|xử lý|phân tích|chuyên|tập trung|phụ trách)", top_text, re.I))
            if is_header and not has_content:
                log.info(f"[search] purpose query returned header, trying next")
                # Try to find a better result in the list
                for i, chunk in enumerate(highlighted[1:], 1):
                    if re.search(r"(đào tạo|lưu trữ|xử lý|phân tích|chuyên|tập trung|phụ trách)", chunk.text, re.I):
                        # Swap to top
                        highlighted[0], highlighted[i] = highlighted[i], highlighted[0]
                        break

        # Intent mismatch check (log only, don't reject)
        if highlighted:
            mismatch = not _check_intent_mismatch(intent, highlighted[0].text)
            if mismatch:
                log.debug(f"[search] intent={intent} potential mismatch, continuing")

        # Log overlap for debug but don't reject based on it
        top_overlap = _keyword_overlap(query, highlighted[0].text) if highlighted else 0
        log.info(f"[search] intent={intent} top_overlap={round(top_overlap, 3)} "
                 f"text_len={len(highlighted[0].text) if highlighted else 0}")

        # No threshold rejection - trust BM25+Vector ranking
        # Only reject empty results

        self._cache.put_l1(query, highlighted[0])
        return Result(query, highlighted, f"fusion_{intent}")

    def stats(self) -> dict:
        return {
            "store": self._store.stats(),
            "cache": self._cache.stats(),
            "embed_model": EMBED_MODEL,
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
        }