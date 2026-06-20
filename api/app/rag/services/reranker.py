"""Reranker singleton — BAAI/bge-reranker-v2-m3.

Yêu cầu: lazy load, batch, cache theo (query, chunk_id), KHÔNG rerank toàn bộ
(chỉ rerank tập đã prefilter, kích thước nhỏ — xem store.py).
"""

import asyncio
import logging
import threading
from typing import Dict, List, Tuple

from .config import (
    DEVICE,
    RERANK_BATCH_SIZE,
    RERANK_CACHE_MAX,
    RERANK_MODEL,
)

log = logging.getLogger("rag.reranker")


class Reranker:
    """Singleton — lazy load, không load model lúc import/startup."""

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._tokenizer = None
                    inst._model = None
                    inst._dtype = None
                    inst._load_lock = threading.Lock()
                    inst._cache: Dict[Tuple[str, str], float] = {}
                    inst._cache_order: List[Tuple[str, str]] = []
                    cls._instance = inst
        return cls._instance

    def _load(self):
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            log.info(f"[reranker] loading {RERANK_MODEL} ...")
            self._dtype = torch.float16 if DEVICE == "cuda" else torch.float32
            self._tokenizer = AutoTokenizer.from_pretrained(RERANK_MODEL)
            self._model = (
                AutoModelForSequenceClassification.from_pretrained(
                    RERANK_MODEL, torch_dtype=self._dtype
                )
                .to(DEVICE)
                .eval()
            )
            log.info(f"[reranker] ready on {DEVICE}")

    def _cache_get(self, key: Tuple[str, str]):
        return self._cache.get(key)

    def _cache_put(self, key: Tuple[str, str], value: float):
        if len(self._cache) >= RERANK_CACHE_MAX:
            old = self._cache_order.pop(0)
            self._cache.pop(old, None)
        self._cache[key] = value
        self._cache_order.append(key)

    def rerank(self, query: str, candidates: List[Tuple[str, str]]) -> List[float]:
        """candidates: list[(chunk_id, text)]. Trả về score cùng thứ tự đầu vào."""
        if not candidates:
            return []

        scores: List = [None] * len(candidates)
        to_compute: List[int] = []
        for i, (cid, _text) in enumerate(candidates):
            cached = self._cache_get((query, cid))
            if cached is not None:
                scores[i] = cached
            else:
                to_compute.append(i)

        if to_compute:
            import torch

            self._load()
            with torch.no_grad():
                for start in range(0, len(to_compute), RERANK_BATCH_SIZE):
                    batch_idx = to_compute[start : start + RERANK_BATCH_SIZE]
                    pairs = [[query, candidates[i][1]] for i in batch_idx]
                    inputs = self._tokenizer(
                        pairs,
                        padding=True,
                        truncation=True,
                        return_tensors="pt",
                        max_length=512,
                    )
                    if DEVICE == "cuda":
                        inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
                    logits = self._model(**inputs).logits.view(-1)
                    if self._dtype == torch.float16:
                        logits = logits.float()
                    batch_scores = torch.sigmoid(logits).cpu().tolist()
                    for i, s in zip(batch_idx, batch_scores):
                        scores[i] = s
                        self._cache_put((query, candidates[i][0]), s)

        return scores  # type: ignore[return-value]

    async def arerank(self, query: str, candidates: List[Tuple[str, str]]) -> List[float]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.rerank, query, candidates)


_reranker_singleton = Reranker()


def get_reranker() -> Reranker:
    return _reranker_singleton
