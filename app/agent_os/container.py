"""
agent_os/container.py

Service accessor — lazy initialization với asyncio.Lock.
Composition root: nơi DUY NHẤT import cả agent_os + Django layer.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import litellm

logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("litellm").setLevel(logging.WARNING)

# =========================================================
# ENV BOOTSTRAP
# =========================================================

if not os.environ.get("OPENROUTER_API_KEY"):
    _env_candidates = [
        Path(__file__).resolve().parents[4] / ".envs" / ".local" / ".django",
        Path(__file__).resolve().parents[4] / ".envs" / ".production" / ".django",
    ]
    for _env_file in _env_candidates:
        if not _env_file.exists():
            continue
        for _line in _env_file.read_text().splitlines():
            _line = _line.strip()
            if _line.startswith("OPENROUTER_API_KEY="):
                os.environ["OPENROUTER_API_KEY"] = _line.split("=", 1)[1].strip()
                break
        if os.environ.get("OPENROUTER_API_KEY"):
            break

if os.environ.get("OPENROUTER_API_KEY"):
    litellm.openrouter_api_key = os.environ["OPENROUTER_API_KEY"]


# =========================================================
# TYPE CHECKING ONLY
# =========================================================

if TYPE_CHECKING:
    from agent_os.rag.rag_zero_v21 import RAG
    from agent_os.rag.document_loader_service import DocumentLoader
    from agent_os.system.runtime.runtime_engine import LLMFactory


logger = logging.getLogger(__name__)


# =========================================================
# RUNTIME CONTAINER
# =========================================================

@dataclass
class AgentServices:
    """
    Global runtime service registry.
    Immutable sau khi bootstrap.
    """

    llm_factory:     LLMFactory
    rag:             RAG | None      # ← Thay knowledge_engine + ingest + retrieval
    document_loader: DocumentLoader | None

    @property
    def rag_available(self) -> bool:
        return self.rag is not None


# =========================================================
# PRIVATE SINGLETON STATE
# =========================================================

_services: AgentServices | None = None
_lock: asyncio.Lock | None = None


# =========================================================
# LOCK FACTORY
# =========================================================

def _get_lock() -> asyncio.Lock:
    global _lock
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _lock is None or (current_loop and _lock._loop is not current_loop):
        _lock = asyncio.Lock()

    return _lock


# =========================================================
# PUBLIC ACCESSOR
# =========================================================

async def get_ctx() -> AgentServices:
    global _services

    if _services is not None:
        return _services

    async with _get_lock():
        if _services is not None:
            return _services

        logger.info("[AgentServices] Khởi tạo runtime services...")
        _services = await _bootstrap()
        logger.info(
            "[AgentServices] READY | RAG=%s",
            "ON" if _services.rag_available else "OFF",
        )

    return _services


# =========================================================
# BOOTSTRAP — RAG ZERO v2.1
# =========================================================

async def _bootstrap() -> AgentServices:
    """
    Khởi tạo: LLM factory + RAG ZERO v2.1 + DocumentLoader.
    Không còn KnowledgeEngine, IngestionService, RetrievalService cũ.
    """

    # 1. Runtime engine (LLM factory)
    from agent_os.system.runtime.runtime_engine import build_runtime
    runtime_data = build_runtime()
    llm_factory = runtime_data["llm_factory"]

    # 2. RAG ZERO v2.1 — tự khởi tạo embed model + store
    from agent_os.rag.rag_service import RAG
    try:
        rag = RAG()
    except Exception:
        logger.exception("[AgentServices] RAG khởi tạo thất bại")
        rag = None

    # 3. DocumentLoader — load file cho RAG
    from agent_os.rag.document_loader_service import DocumentLoader
    try:
        document_loader = DocumentLoader()
    except Exception:
        logger.exception("[AgentServices] DocumentLoader khởi tạo thất bại")
        document_loader = None

    return AgentServices(
        llm_factory=llm_factory,
        rag=rag,
        document_loader=document_loader,
    )


# =========================================================
# ISOLATED BOOTSTRAP — Celery Worker
# =========================================================

async def create_isolated_services() -> AgentServices:
    logger.info("[AgentServices] Khởi tạo Isolated Services...")
    return await _bootstrap()