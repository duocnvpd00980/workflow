# agent_os/container.py
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, AsyncGenerator

from fastapi import FastAPI

if TYPE_CHECKING:
    from agent_os.rag.rag_service import RAG
    from agent_os.rag.document_loader_service import DocumentLoader
    from agent_os.system.runtime.runtime_engine import ModelRegistry

logger = logging.getLogger(__name__)


@dataclass
class Services:
    registry: ModelRegistry
    rag: RAG | None
    loader: DocumentLoader | None

    @property
    def rag_ok(self) -> bool:
        return self.rag is not None


_svc: Services | None = None


def get_ctx() -> Services:
    assert _svc is not None, "Services not initialized"
    return _svc


async def _bootstrap() -> Services:
    from agent_os.system.runtime.runtime_engine import build_runtime
    from agent_os.rag.rag_service import RAG
    from agent_os.rag.document_loader_service import DocumentLoader

    rag, loader = None, None
    try:
        rag = RAG()
    except Exception:
        logger.exception("[Services] RAG init failed")
    try:
        loader = DocumentLoader()
    except Exception:
        logger.exception("[Services] DocumentLoader init failed")

    return Services(registry=build_runtime()["registry"], rag=rag, loader=loader)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _svc
    logger.info("[Services] Bootstrapping...")
    _svc = await _bootstrap()
    logger.info("[Services] READY | RAG=%s", "ON" if _svc.rag_ok else "OFF")
    yield
    _svc = None  # cleanup