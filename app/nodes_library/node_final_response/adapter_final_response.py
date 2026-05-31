from __future__ import annotations
import logging
from langchain_core.runnables import RunnableConfig
from app.core.main_bus import MainBus
from app.core.registry import BusRegistry
from app.core.protocol import StandardFrame, BodyFrame

log = logging.getLogger(__name__)


async def node_final_response(state: MainBus, config: RunnableConfig = None) -> dict:
    upstream_payload = None
    flow_type = "chat"

    if (
        hasattr(state, "cache_read")
        and state.cache_read
        and state.cache_read.payload.route == "hit"
    ):
        upstream_payload = state.cache_read.payload
        flow_type = "cache"

    elif hasattr(state, "output_guard") and state.output_guard:
        upstream_payload = state.output_guard.payload
        flow_type = "knowledge"

    elif hasattr(state, "fallback_search") and state.fallback_search:
        upstream_payload = state.fallback_search.payload
        flow_type = "fallback"

    if not upstream_payload or upstream_payload.status != "SUCCESS":
        log.warning("[node_final_response] No valid upstream payload")
        return StandardFrame.emit(
            registry_key=BusRegistry.FR,
            payload=BodyFrame(
                status="FAILED",
                text="Xin lỗi, hệ thống không thể tạo phản hồi lúc này.",
                error="DATA_FLOW_EMPTY",
            ),
        )

    log.info("[node_final_response] flow=%s text_len=%d", flow_type, len(upstream_payload.text))

    return StandardFrame.emit(
        registry_key=BusRegistry.FR,
        payload=BodyFrame(
            status="SUCCESS",
            text=upstream_payload.text,
            records=[],
            state={"flow_type": flow_type},
            error=None,
        ),
    )