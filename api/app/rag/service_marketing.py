"""RAG ZERO v3.1 — BGE-M3 + bge-reranker-v2-m3, SOTA multilingual RAG.

MARKETING EDITION: Thêm business_id filter, document_type filter, marketing metadata.
"""

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

PERSIST_DIR = Path(__file__).parent.parent.parent / "rag_storage"
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

# ── Marketing Document Types ──────────────────────────────────────────────────
# Các loại document dùng cho marketing content generation

MARKETING_DOC_TYPES = {
    "brand_guideline": "🎨 Hướng dẫn Thương hiệu",
    "product_knowledge": "📚 Kiến thức Sản phẩm",
    "competitor_analysis": "📊 Phân tích Đối thủ",
    "web_page": "🌐 Trang Web",
    "keyword_research": "🔍 Nghiên cứu Từ khóa",
    "social_content": "📱 Nội dung Mạng xã hội",
    "user_feedback": "💬 Phản hồi Khách hàng",
    "serp_competitor": "🏆 Đối thủ SERP",
    "campaign_brief": "📋 Brief Chiến dịch",
    "menu_data": "🍽️ Dữ liệu Thực đơn",
    "review_data": "⭐ Đánh giá Khách hàng",
    "brand_identity": "🏷️ Nhận diện Thương hiệu",
    "contact_cta": "📞 Liên hệ & CTA",
    "products": "🦐 Sản phẩm/Dịch vụ",
}

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

_TOKEN_RE = re.compile(r"[\wÀ-ɏḀ-ỿ]+", re.UNICODE)

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


class Embedder:
    def __init__(self):
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        log.info(f"[embed] loading {EMBED_MODEL}...")
        self._model = SentenceTransformer(EMBED_MODEL)
        log.info("[embed] loaded")

    async def encode(self, texts: List[str]) -> np.ndarray:
        self._load()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self._model.encode(texts, normalize_embeddings=True)
        )

# ── Reranker (lazy-load) ──────────────────────────────────────────────────────

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
# MARKETING: Thêm business_id và document_type filter

class Store:
    def __init__(self, embed: Embedder):
        self._embed = embed
        self._idx = faiss.IndexFlatIP(DIM)
        self._texts: List[str] = []
        self._metas: List[dict] = []
        self._bm25_corpus: List[List[str]] = []
        self._bm25: Optional[BM25Okapi] = None
        self._hashes: Set[str] = set()
        self._lock = asyncio.Lock()
        PERSIST_DIR.mkdir(exist_ok=True)

    async def add(self, doc: Doc) -> str:
        text = doc.text.strip()
        if not text:
            return "skipped"
        h = hashlib.sha256(text.encode()).hexdigest()[:16]
        if h in self._hashes:
            return "duplicate"

        async with self._lock:
            if h in self._hashes:
                return "duplicate"

            chunks = self._chunk(text)
            meta = {"source_id": doc.metadata.get("source_id", h), **doc.metadata}

            embs_list = await self._embed.encode(chunks)
            embs = np.array(embs_list, dtype=np.float32)
            faiss.normalize_L2(embs)
            self._idx.add(embs)

            for i, c in enumerate(chunks):
                self._texts.append(c)
                self._metas.append({**meta, "chunk_idx": i})
                self._bm25_corpus.append(_tokenize(c))

            self._bm25 = BM25Okapi(self._bm25_corpus)
            self._hashes.add(h)
            await self._save()
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

    # MARKETING: Thêm business_id filter
    async def vector(self, query: str, k: int, business_id: Optional[str] = None) -> List[Chunk]:
        if not self._idx.ntotal:
            return []
        emb = await self._embed.encode([query])
        v = _vec(emb[0])
        # Lấy nhiều hơn để có đủ sau filter
        scores, ids = self._idx.search(v, k * 5)

        chunks = []
        for s, i in zip(scores[0], ids[0]):
            if i < 0 or s <= 0:
                continue
            meta = self._metas[i]
            # Filter by business_id
            if business_id and meta.get("business_id") != business_id:
                continue
            chunks.append(Chunk(float(s), self._texts[i], meta))
            if len(chunks) >= k:
                break
        return chunks

    # MARKETING: Thêm business_id filter
    def bm25(self, queries: List[str], k: int, business_id: Optional[str] = None) -> List[Chunk]:
        if not self._bm25:
            return []
        tokenized = [_tokenize(q) for q in queries]
        raw = np.max([self._bm25.get_scores(t) for t in tokenized], axis=0)
        top = np.argsort(raw)[::-1][:k * 5]  # Lấy nhiều hơn để filter
        if not len(top):
            return []
        mx = raw.max() or 1.0
        best = raw[top[0]]

        results = []
        for i in top:
            if raw[i] <= 0 or raw[i] < best * BM25_MIN_RATIO:
                continue
            meta = self._metas[i]
            if business_id and meta.get("business_id") != business_id:
                continue
            results.append(Chunk(float(raw[i] / mx), self._texts[i], meta))
            if len(results) >= k:
                break
        return results

    def stats(self) -> dict:
        return {"chunks": len(self._texts), "hashes": len(self._hashes), "faiss_vectors": self._idx.ntotal}

    def _save_sync(self):
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

    async def _save(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_sync)

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
# MARKETING: Thêm business_id và document_type filter

class RAG:
    def __init__(self):
        self._embed = Embedder()
        self._reranker = Reranker()
        self._store = None
        self._cache = Cache()

    async def _lazy_init(self):
        if self._store is None:
            self._store = Store(self._embed)
            self._store._load()

    async def add(self, text: str, **meta) -> str:
        if self._store is None:
            await self._lazy_init()
        return await self._store.add(Doc(text, meta))

    async def search(
        self,
        query: str,
        top_k: int = FINAL_K,
        document_type: Optional[str] = None,
        business_id: Optional[str] = None,
    ) -> Result:
        if self._store is None:
            await self._lazy_init()

        query = query.strip()
        intent = _detect_intent(query)

        # L1 exact cache
        cache_key = f"{query}:{business_id}:{document_type}"
        if cached := self._cache.get(cache_key):
            return Result(query, cached, "cache_l1")

        # Step 1: Retrieve với business_id filter
        variants = expand_query(query)
        bm25_hits = self._store.bm25(variants, RETRIEVE_K, business_id=business_id)
        vec_hits = await self._store.vector(variants[0], RETRIEVE_K, business_id=business_id)

        # Filter by document_type nếu có
        if document_type:
            bm25_hits = [c for c in bm25_hits if c.meta.get("document_type") == document_type]
            vec_hits = [c for c in vec_hits if c.meta.get("document_type") == document_type]

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
            log.info(f"[search] intent={intent} business_id={business_id} doc_type={document_type} "
                     f"rerank_top={round(reranked[0][1], 4)} retrieve={len(fused)} final={len(highlighted)}")

        self._cache.put(cache_key, highlighted)
        return Result(query, highlighted, f"reranked_{intent}")

    def stats(self) -> dict:
        return {
            "store": self._store.stats() if self._store else {"chunks": 0, "hashes": 0, "faiss_vectors": 0},
            "cache": self._cache.stats(),
            "embed_model": EMBED_MODEL,
            "rerank_model": RERANK_MODEL,
            "device": DEVICE,
        }


# ── Marketing RAG Wrapper ───────────────────────────────────────────────────
# Helper class cho marketing-specific queries

class MarketingRAG:
    """Wrapper around RAG với marketing-specific search strategies."""

    def __init__(self, rag: RAG):
        self._rag = rag

    async def search_for_content(
        self,
        query: str,
        business_id: str,
        content_type: str,  # "blog" | "email" | "social" | "ads"
        top_k: int = 5,
    ) -> Result:
        """Search optimized cho content generation.

        Weight: brand_core > keyword_research > social_content > user_feedback
        """
        # Search từng document type riêng biệt rồi merge
        doc_types = {
            "blog": ["brand_guideline", "brand_identity", "keyword_research", "products"],
            "email": ["brand_guideline", "contact_cta", "products", "campaign_brief"],
            "social": ["brand_identity", "social_content", "products", "user_feedback"],
            "ads": ["brand_guideline", "contact_cta", "keyword_research", "competitor_analysis"],
        }

        target_types = doc_types.get(content_type, ["brand_guideline"])
        all_chunks = []

        for doc_type in target_types:
            result = await self._rag.search(
                query,
                top_k=top_k // len(target_types) + 2,
                document_type=doc_type,
                business_id=business_id,
            )
            all_chunks.extend(result.chunks)

        # Deduplicate và sort by score
        seen = set()
        unique_chunks = []
        for c in sorted(all_chunks, key=lambda x: x.score, reverse=True):
            key = hashlib.md5(c.text.encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                unique_chunks.append(c)

        return Result(query, unique_chunks[:top_k], "marketing_merged")


# ── Image Embedder ────────────────────────────────────────────────────────────

IMAGE_EMBED_MODEL = "google/siglip-base-patch16-224"
IMAGE_DIM = 768
IMAGE_PERSIST_DIR = Path(__file__).parent.parent.parent / "rag_storage" / "image"

class ImageEmbedder:
    def __init__(self):
        self._processor = None
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        from transformers import AutoProcessor, AutoModel
        log.info(f"[image_embed] loading {IMAGE_EMBED_MODEL}...")
        self._processor = AutoProcessor.from_pretrained(IMAGE_EMBED_MODEL)
        self._model = AutoModel.from_pretrained(IMAGE_EMBED_MODEL)
        self._model.eval()
        log.info("[image_embed] loaded")

    async def encode(self, images: List["Image.Image"]) -> np.ndarray:
        self._load()
        loop = asyncio.get_running_loop()

        def _run():
            inputs = self._processor(images=images, return_tensors="pt")
            with torch.no_grad():
                outputs = self._model.vision_model(**inputs)
                emb = outputs.pooler_output
            emb = emb / emb.norm(dim=-1, keepdim=True)
            return emb.cpu().numpy()

        return await loop.run_in_executor(None, _run)

    async def encode_text(self, texts: List[str]) -> np.ndarray:
        self._load()
        loop = asyncio.get_running_loop()

        def _run():
            inputs = self._processor(text=texts, return_tensors="pt", padding=True, truncation=True)
            with torch.no_grad():
                outputs = self._model.text_model(**inputs)
                emb = outputs.pooler_output
            emb = emb / emb.norm(dim=-1, keepdim=True)
            return emb.cpu().numpy()

        return await loop.run_in_executor(None, _run)


# ── Image Store ───────────────────────────────────────────────────────────────

class ImageStore:
    def __init__(self, embed: ImageEmbedder):
        self._embed = embed
        self._idx = faiss.IndexFlatIP(IMAGE_DIM)
        self._ids: List[str] = []
        self._metas: List[dict] = []
        self._hashes: Set[str] = set()
        self._lock = asyncio.Lock()
        IMAGE_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

    async def add(self, image: "Image.Image", image_id: str, **meta) -> str:
        h = hashlib.sha256(image_id.encode()).hexdigest()[:16]
        if h in self._hashes:
            return "duplicate"

        async with self._lock:
            if h in self._hashes:
                return "duplicate"

            embs = await self._embed.encode([image])
            emb = np.array(embs, dtype=np.float32)
            faiss.normalize_L2(emb)
            self._idx.add(emb)

            self._ids.append(image_id)
            self._metas.append({"image_id": image_id, **meta})
            self._hashes.add(h)
            await self._save()
            log.info(f"[image_add] {image_id}")
            return "ok"

    async def search(self, image: "Image.Image", k: int = 5) -> List[dict]:
        if not self._idx.ntotal:
            return []
        embs = await self._embed.encode([image])
        v = np.array(embs, dtype=np.float32)
        faiss.normalize_L2(v)
        scores, ids = self._idx.search(v, k)
        return [
            {"image_id": self._ids[i], "score": float(s), "meta": self._metas[i]}
            for s, i in zip(scores[0], ids[0])
            if i >= 0 and s > 0
        ]

    async def search_by_text(self, text: str, k: int = 5) -> List[dict]:
        if not self._idx.ntotal:
            return []
        embs = await self._embed.encode_text([text])
        v = np.array(embs, dtype=np.float32)
        faiss.normalize_L2(v)
        scores, ids = self._idx.search(v, k)
        return [
            {"image_id": self._ids[i], "score": float(s), "meta": self._metas[i]}
            for s, i in zip(scores[0], ids[0])
            if i >= 0
        ]

    def stats(self) -> dict:
        return {"images": len(self._ids), "faiss_vectors": self._idx.ntotal}

    def _save_sync(self):
        data = {"ids": self._ids, "metas": self._metas, "hashes": list(self._hashes)}
        tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=IMAGE_PERSIST_DIR, delete=False, suffix=".tmp")
        try:
            json.dump(data, tmp, ensure_ascii=False)
            tmp.close()
            os.replace(tmp.name, IMAGE_PERSIST_DIR / "data.json")
        except Exception:
            os.unlink(tmp.name)
            raise
        tmp_idx = tempfile.NamedTemporaryFile(dir=IMAGE_PERSIST_DIR, delete=False, suffix=".tmp")
        try:
            tmp_idx.close()
            faiss.write_index(self._idx, tmp_idx.name)
            os.replace(tmp_idx.name, IMAGE_PERSIST_DIR / "faiss.index")
        except Exception:
            os.path.exists(tmp_idx.name) and os.unlink(tmp_idx.name)
            raise

    async def _save(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_sync)

    def _load(self):
        dp = IMAGE_PERSIST_DIR / "data.json"
        fp = IMAGE_PERSIST_DIR / "faiss.index"
        if not (dp.exists() and fp.exists()):
            return
        try:
            with open(dp, encoding="utf-8") as f:
                d = json.load(f)
            self._ids = d["ids"]
            self._metas = d["metas"]
            self._hashes = set(d["hashes"])
            self._idx = faiss.read_index(str(fp))
            log.info(f"[image_load] {len(self._ids)} images restored")
        except Exception as e:
            log.warning(f"[image_load] corrupt, starting fresh: {e}")
            self._ids, self._metas, self._hashes = [], [], set()
            self._idx = faiss.IndexFlatIP(IMAGE_DIM)


# ── Image RAG ─────────────────────────────────────────────────────────────────

class ImageRAG:
    def __init__(self):
        self._embed = ImageEmbedder()
        self._store: Optional[ImageStore] = None

    async def _lazy_init(self):
        if self._store is None:
            self._store = ImageStore(self._embed)
            self._store._load()

    async def add(self, image: "Image.Image", image_id: str, **meta) -> str:
        await self._lazy_init()
        return await self._store.add(image, image_id, **meta)

    async def search(self, image: "Image.Image", k: int = 5) -> List[dict]:
        await self._lazy_init()
        return await self._store.search(image, k)

    async def search_by_text(self, text: str, k: int = 5) -> List[dict]:
        await self._lazy_init()
        return await self._store.search_by_text(text, k)

    def stats(self) -> dict:
        return self._store.stats() if self._store else {"images": 0, "faiss_vectors": 0}