from __future__ import annotations

import logging

from langchain_core.runnables import RunnableConfig

from app.core.main_bus import MainBus
from app.core.protocol  import BodyFrame, StandardFrame
from app.core.registry  import BusRegistry

from .cache_layer_service import CacheLayerService


logger = logging.getLogger(__name__)

# =========================================================
# CACHE CONFIG
# =========================================================

_cache = CacheLayerService(
    ttl_hours=24,
    max_entries=10000,
)

# =========================================================
# INVALID CACHE CONTENT
# =========================================================

INVALID_CACHE_PATTERNS = {
    "DI Error",
    "Traceback",
    "ModuleNotFoundError",
    "ValidationError",
    "Lỗi hệ thống",
    "Internal Server Error",
}


# =========================================================
# CACHE WRITE NODE
# =========================================================


async def node_cache_write(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:
    """
    ======================================================================
    CACHE_WRITE — WRITE NODE
    ======================================================================

    Chỉ cache response hợp lệ:
    - status == SUCCESS
    - không có error
    - có answer text
    - không chứa lỗi hệ thống

    Node này KHÔNG BAO GIỜ block pipeline nếu cache fail.

    ======================================================================
    """

    # =====================================================
    # EXTRACT USER QUERY
    # =====================================================

    user_query = ""

    try:
        if hasattr(state, "input_guard") and state.input_guard:
            user_query = (getattr(state.input_guard.payload, "text", "") or "").strip()

    except Exception:
        logger.exception("[CACHE_WRITE] Failed extracting user_query")

    # =====================================================
    # EXTRACT GENERATION PAYLOAD
    # =====================================================

    generation_payload = None

    try:
        if hasattr(state, "generation") and state.generation:
            generation_payload = getattr(
                state.generation,
                "payload",
                None,
            )

        elif hasattr(state, "output_guard") and state.output_guard:
            generation_payload = getattr(
                state.output_guard,
                "payload",
                None,
            )

    except Exception:
        logger.exception("[CACHE_WRITE] Failed extracting payload")

    # =====================================================
    # VALIDATE RESPONSE
    # =====================================================

    answer = ""
    is_success = False

    if generation_payload:
        answer = (getattr(generation_payload, "text", "") or "").strip()

        status = getattr(generation_payload, "status", "")
        error = getattr(generation_payload, "error", None)

        is_success = status == "SUCCESS" and not error

    # =====================================================
    # CACHE FILTER
    # =====================================================

    contains_invalid_pattern = any(
        pattern in answer for pattern in INVALID_CACHE_PATTERNS
    )

    is_valid_answer = bool(answer) and not contains_invalid_pattern

    # =====================================================
    # WRITE CACHE
    # =====================================================

    try:
        if user_query and is_success and is_valid_answer:
            _cache.store(
                user_query,
                answer,
            )

            logger.info(
                "[CACHE_WRITE] Stored | query=%s",
                user_query,
            )

        else:
            logger.warning(
                ("[CACHE_WRITE] Skip cache | query=%s success=%s valid=%s"),
                user_query,
                is_success,
                is_valid_answer,
            )

    except Exception:
        logger.exception("[CACHE_WRITE] Store failed")

    # =====================================================
    # PASS-THROUGH
    # =====================================================

    return StandardFrame.emit(
        registry_key=BusRegistry.CW,
        payload=BodyFrame(
            status="SUCCESS",
            text=answer,
            state={
                "process_completed": True,
            },
            error=None,
        ),
    )
