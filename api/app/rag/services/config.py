"""Cấu hình tập trung cho toàn bộ RAG system."""

import os
from pathlib import Path

# ── Models ───────────────────────────────────────────────────────────────────
EMBED_MODEL = "BAAI/bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
EMBED_DIM = 1024

# CPU-first: chỉ dùng GPU khi có sẵn và không bị ép buộc qua env.
DEVICE = os.environ.get("RAG_DEVICE") or "cpu"

# ── Storage ──────────────────────────────────────────────────────────────────
PERSIST_ROOT = Path(os.environ.get("RAG_STORAGE_DIR", "")) if os.environ.get("RAG_STORAGE_DIR") else (
    Path(__file__).resolve().parent.parent / "rag_storage"
)

# ── Pipeline: retrieve -> prefilter -> rerank -> final ──────────────────────
RETRIEVE_K = 40
PREFILTER_K = 15
RERANK_K = 8
FINAL_K = 5

# ── Rerank ───────────────────────────────────────────────────────────────────
RERANK_BATCH_SIZE = 8
RERANK_CACHE_MAX = 5000

# ── Search result cache (per store) ─────────────────────────────────────────
RESULT_CACHE_MAX = 500

# ── Hybrid search weights theo loại RAG (vector_weight, bm25_weight) ────────
WEIGHTS = {
    "keyword": {"vector": 0.30, "bm25": 0.70},
    "comment": {"vector": 0.80, "bm25": 0.20},
    "social": {"vector": 0.60, "bm25": 0.40},
}
