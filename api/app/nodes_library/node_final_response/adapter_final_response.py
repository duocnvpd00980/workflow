from __future__ import annotations
import logging
from langchain_core.runnables import RunnableConfig
from app.core.main_bus import MainBus
from app.core.registry import BusRegistry
from app.core.protocol import StandardFrame, BodyFrame

log = logging.getLogger(__name__)


async def node_final_response(state: MainBus, config: RunnableConfig = None) -> dict:
    payload = None

    if state.cache_read and state.cache_read.payload.route == "hit":
        payload = state.cache_read.payload
    elif state.output_guard:
        payload = state.output_guard.payload
    elif state.fallback_search:
        payload = state.fallback_search.payload

    if not payload or payload.status != "SUCCESS" or not payload.text:
        log.warning("[final_response] no valid upstream payload")
        return StandardFrame.emit(
            registry_key=BusRegistry.FR,
            payload=BodyFrame(status="FAILED", text="", error="DATA_FLOW_EMPTY"),
        )

    return StandardFrame.emit(
        registry_key=BusRegistry.FR,
        payload=BodyFrame(status="SUCCESS", text=payload.text, error=None),
    )