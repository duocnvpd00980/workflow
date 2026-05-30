from __future__ import annotations
from langchain_core.runnables import RunnableConfig
from app.core.main_bus import MainBus
from app.core.registry  import BusRegistry
from app.core.protocol  import StandardFrame, BodyFrame
from app.container import get_ctx
from .generation_service import GenerationService

_service = GenerationService()

import logging

log = logging.getLogger(__name__)


async def node_generation(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:

    log.info("[DEBUG] --- Bắt đầu node_generation ---")

    # 1. TRÍCH XUẤT NGỮ CẢNH
    relevance_frame = getattr(state, "relevance_check", None)
    log.info(f"[DEBUG] Relevance Frame tồn tại: {relevance_frame is not None}")

    rag_context = "Không có thông tin."
    if relevance_frame and hasattr(relevance_frame, "payload"):
        log.info(f"[DEBUG] Relevance Status: {relevance_frame.payload.status}")
        rag_context = (
            relevance_frame.payload.text
            if relevance_frame.payload.status == "SUCCESS"
            else "RAG Fail"
        )

    chat_history = getattr(state, "messages", [])
    log.info(f"[DEBUG] Số lượng tin nhắn history: {len(chat_history)}")

    user_input = getattr(state.input_guard.payload, "text", "")
    log.info(f"[DEBUG] User Input: {user_input}")

    # 2. DEPENDENCY INJECTION
    try:
        ctx = await get_ctx()
        llm_engine = ctx.llm_factory.get_model("default")
        log.info("[DEBUG] LLM Engine đã khởi tạo thành công.")
    except Exception as e:
        log.error(f"[DEBUG] Lỗi khởi tạo LLM Engine: {e}")
        return _emit_error(f"DI Error: {e}")

    # 3. THỰC THI (Domain Execution)
    try:
        log.info("[DEBUG] Đang gọi _service.run...")
        result = await _service.run(
            user_input=user_input,
            chat_history=chat_history,
            rag_context=rag_context,
            llm_engine=llm_engine,
        )
        log.info(f"[DEBUG] Service trả về: {result.model_dump()}")

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
        # CỰC KỲ QUAN TRỌNG: In ra traceback đầy đủ
        log.exception(f"[DEBUG] CRITICAL ERROR trong Generation: {e}")
        return StandardFrame.emit(
            registry_key=BusRegistry.GEN,
            payload=BodyFrame(
                status="FAILED",
                text=f"Lỗi chi tiết: {str(e)}",  # Hiển thị lỗi ra UI để cậu đọc
                error=f"[node_generation] {e!r}",
            ),
        )


def _emit_error(msg):
    return StandardFrame.emit(
        registry_key=BusRegistry.GEN,
        payload=BodyFrame(status="FAILED", text=msg, error=msg),
    )
