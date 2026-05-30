from __future__ import annotations
import logging

from langchain_core.runnables import RunnableConfig

from app.core.main_bus import MainBus
from app.core.registry import BusRegistry
from app.core.protocol import StandardFrame, BodyFrame
from app.core.deps import get_llm
from .generation_service import GenerationService

log = logging.getLogger(__name__)
_service = GenerationService()


async def node_generation(state: MainBus, config: RunnableConfig = None) -> dict:

    # 1. TRÍCH XUẤT NGỮ CẢNH
    relevance_frame = getattr(state, "relevance_check", None)
    rag_context = "Không có thông tin."
    if relevance_frame and hasattr(relevance_frame, "payload"):
        rag_context = (
            relevance_frame.payload.text
            if relevance_frame.payload.status == "SUCCESS"
            else "Không có thông tin."
        )

    chat_history = getattr(state, "messages", [])
    user_input = getattr(state.input_guard.payload, "text", "")

    # 2. DEPENDENCY INJECTION
    try:
        llm = get_llm().llm()
    except Exception as e:
        log.error("[node_generation] DI failed: %s", e)
        return _emit_error(f"DI Error: {e}")

    # 3. THỰC THI
    try:
        result = await _service.run(
            user_input=user_input,
            chat_history=chat_history,
            rag_context=rag_context,
            llm=llm,
        )
        return StandardFrame.emit(
            registry_key=BusRegistry.GEN,
            payload=BodyFrame(
                status="SUCCESS",
                text=result.response,
                records=[result.model_dump()],
                state={"process_completed": True, "tone": result.tone},
                error=None,
            ),
        )
    except Exception as e:
        log.exception("[node_generation] failed: %s", e)
        return _emit_error(str(e))


def _emit_error(msg: str) -> dict:
    return StandardFrame.emit(
        registry_key=BusRegistry.GEN,
        payload=BodyFrame(status="FAILED", text=msg, error=msg),
    )