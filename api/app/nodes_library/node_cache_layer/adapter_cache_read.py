from __future__ import annotations
from langchain_core.runnables import RunnableConfig
from app.core.main_bus import MainBus
from app.core.registry  import BusRegistry
from app.core.protocol  import StandardFrame, BodyFrame
from .cache_layer_service import CacheLayerService

_cache = CacheLayerService(ttl_hours=24, max_entries=10000)


async def node_cache_read(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:
    """
    ======================================================================
    CACHE_LAYER — READ NODE
    ======================================================================
    Lookup answer cache. Hit → final_response. Miss → knowledge_base.
    End → __end__ (lỗi nghiêm trọng).
    ======================================================================
    """

    # POST-GUARD
    error_message = None
    if not hasattr(state, "heuristic_router") or state.heuristic_router is None:
        error_message = (
            "[CACHE_LAYER] Topology Violation: heuristic_router không tồn tại."
        )
    elif getattr(state.heuristic_router.payload, "status", None) != "SUCCESS":
        error_message = (
            f"[CACHE_LAYER] Upstream Failure: {state.heuristic_router.payload.error}"
        )

    if error_message:
        return StandardFrame.emit(
            registry_key=BusRegistry.CR,
            payload=BodyFrame(
                status="FAILED",
                route="end",
                text="",
                state={"process_completed": False},
                error=error_message,
            ),
        )

    # EXTRACT QUERY
    user_query = getattr(state.heuristic_router.payload, "text", "")
    if not user_query:
        return StandardFrame.emit(
            registry_key=BusRegistry.CR,
            payload=BodyFrame(
                status="FAILED",
                route="end",
                text="",
                state={"process_completed": False},
                error="[CACHE_LAYER] Empty query.",
            ),
        )

    # CACHE LOOKUP
    cache_result = await _cache.run(user_query)

    # EMIT
    if cache_result.cache_status == "hit":
        return StandardFrame.emit(
            registry_key=BusRegistry.CR,
            payload=BodyFrame(
                status="SUCCESS",
                route="hit",  # → final_response
                text=cache_result.cached_answer,
                state={
                    "process_completed": True,
                    "cache_status": "hit",
                    "query": user_query,
                },
                metrics={
                    "cache_tier": cache_result.cache_tier,
                    "similarity_score": cache_result.similarity_score,
                },
                error=None,
            ),
        )

    # Miss → knowledge_base (RAG)
    return StandardFrame.emit(
        registry_key=BusRegistry.CR,
        payload=BodyFrame(
            status="SUCCESS",
            route="miss",  # → knowledge_base
            text=user_query,
            state={
                "process_completed": False,
                "cache_status": "miss",
                "query": user_query,
            },
            metrics={"cache_tier": "none", "similarity_score": 0.0},
            error=None,
        ),
    )
