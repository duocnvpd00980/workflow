"""Embedder singleton — BAAI/bge-m3, normalize, async, dùng chung cho cả 3 RAG."""

import asyncio
import gc
import logging
import threading
from typing import List

import numpy as np
import torch

from .config import EMBED_MODEL

log = logging.getLogger("rag.embedder")


class Embedder:
    """Singleton — chỉ load model 1 lần, dùng chung toàn process."""

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._model = None
                    inst._load_lock = threading.Lock()
                    cls._instance = inst
        return cls._instance

    def unload(self):
        """Giải phóng hoàn toàn model + VRAM."""
        if self._model is not None:
            self._model = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            log.info("[embedder] đã unload")

    def _load(self):
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return
            log.info(f"[embedder] loading {EMBED_MODEL} ...")
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(EMBED_MODEL)
            log.info("[embedder] ready")

    async def encode(self, texts: List[str]) -> np.ndarray:
        """Trả về ma trận embedding đã normalize (L2), shape (n, dim)."""
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        self._load()
        loop = asyncio.get_running_loop()

        def _run():
            vecs = self._model.encode(
                texts,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return np.asarray(vecs, dtype=np.float32)

        return await loop.run_in_executor(None, _run)


_embedder_singleton = Embedder()


def get_embedder() -> Embedder:
    return _embedder_singleton
