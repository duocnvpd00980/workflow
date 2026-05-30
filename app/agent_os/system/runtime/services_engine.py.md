"""
agent_os/system/runtime/services.py

Service accessor — lazy initialization với asyncio.Lock.
"""


import asyncio
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentServices:
    llm_factory:      Any
    knowledge_engine: Any
    ingest:           Any
    retrieval:        Any

    @property
    def rag_available(self) -> bool:
        return self.knowledge_engine is not None


_services: AgentServices | None = None
_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


async def get_services() -> AgentServices:
    global _services

    if _services is not None:
        return _services

    async with _get_lock():
        if _services is not None:
            return _services
        logger.info("[AgentServices] Khởi tạo lần đầu...")
        _services = await _bootstrap()
        logger.info(
            "[AgentServices] Sẵn sàng — LLM: OK | RAG: %s",
            "OK" if _services.rag_available else "UNAVAILABLE",
        )

    return _services


async def _bootstrap() -> AgentServices:
    from agent_os.system.knowledge.ingestion_service import IngestionService
    from agent_os.system.knowledge.knowledge_engine import KnowledgeEngine
    from agent_os.system.knowledge.retrieval_service import RetrievalService
    from agent_os.system.runtime.runtime_engine import build_runtime

    runtime_data = build_runtime()
    llm_factory = runtime_data["llm_factory"]

    embed_engine = llm_factory.get_embedding("default_embed")
    try:
        knowledge_engine = await KnowledgeEngine.create(embed_engine=embed_engine)
    except Exception:
        logger.exception("[AgentServices] KnowledgeEngine không khả dụng — RAG tắt")
        knowledge_engine = None

    return AgentServices(
        llm_factory=llm_factory,
        knowledge_engine=knowledge_engine,
        ingest=IngestionService(engine=knowledge_engine) if knowledge_engine else None,
        retrieval=RetrievalService(engine=knowledge_engine) if knowledge_engine else None,
    )