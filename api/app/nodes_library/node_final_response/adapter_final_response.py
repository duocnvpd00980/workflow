from __future__ import annotations
import logging
import time

from langchain_core.runnables import RunnableConfig

from app.core.main_bus import MainBus
from app.core.registry  import BusRegistry
from app.core.protocol  import StandardFrame, BodyFrame
from .final_response_service  import FinalResponseService
from .final_response_protocol import FinishReason

log  = logging.getLogger(__name__)
_svc = FinalResponseService()


async def node_final_response(
    state:  MainBus,
    config: RunnableConfig = None,
) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: NODE_FINAL_RESPONSE
    ======================================================================
    [BUSINESS INTENT]
    Terminal node — tổng hợp câu trả lời cuối từ ba nhánh hội tụ:
      (1) cache_read       --hit-->    final_response  [cache hit]
      (2) output_guard     --direct--> final_response  [rag/llm path]
      (3) fallback_search  --error-->  final_response  [search failed]
    Ưu tiên: cache > output_guard > fallback_search.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard        — ít nhất 1 upstream phải tồn tại.
    - Step 2: Context Extraction     — bóc payload từ đúng thanh ghi.
    - Step 3: Pure Domain Execution  — gọi FinalResponseService.
    - Step 4: Bus Emit               — map vào BodyFrame, emit StandardFrame.
    ======================================================================
    """
    t0 = time.time()

    # ── STEP 1: SAFE POST-GUARD ───────────────────────────────────────────
    has_any = (
        state.cache_read      is not None or
        state.output_guard    is not None or
        state.fallback_search is not None
    )

    if not has_any:
        err = (
            "[NODE_FINAL_RESPONSE] Topology Violation: "
            "Không có upstream nào trên Bus."
        )
        log.error(err)
        return StandardFrame.emit(
            registry_key=BusRegistry.FR,
            payload=BodyFrame(
                status  = "FAILED",
                text    = "",
                state   = {"process_completed": False},
                context = {"topology_error": err},
                error   = err,
            ),
        )

    # ── STEP 2: CONTEXT EXTRACTION ────────────────────────────────────────
    cache_payload  = state.cache_read.payload      if state.cache_read      else None
    guard_payload  = state.output_guard.payload    if state.output_guard    else None
    search_payload = state.fallback_search.payload if state.fallback_search else None

    node_path: list[str] = [
        reg for reg, exists in [
            ("cache_read",      state.cache_read      is not None),
            ("knowledge_base",  state.knowledge_base  is not None),
            ("relevance_check", state.relevance_check is not None),
            ("fallback_search", state.fallback_search is not None),
            ("generation",      state.generation      is not None),
            ("output_guard",    state.output_guard    is not None),
        ] if exists
    ]

    conversation_id = getattr(state, "conversation_id", "")
    msg_id          = getattr(state, "msg_id", "")

    # ── STEP 3: PURE DOMAIN EXECUTION ────────────────────────────────────
    result = _svc.run(
        cache_payload  = cache_payload,
        guard_payload  = guard_payload,
        search_payload = search_payload,
        t0             = t0,
        node_path      = node_path,
    )

    # ── STEP 4: STATUS NORMALIZATION & BUS EMIT ───────────────────────────
    status = "FAILED" if result.finish_reason == FinishReason.ERROR else "SUCCESS"

    log.info(
        "[node_final_response] source=%s finish=%s confidence=%.2f "
        "latency=%.1fms conv=%s path=%s",
        result.answer_source, result.finish_reason,
        result.confidence, result.latency_ms,
        conversation_id, "→".join(node_path),
    )

    return StandardFrame.emit(
        registry_key=BusRegistry.FR,
        payload=BodyFrame(
            status  = status,
            text    = result.answer,
            records = [],
            state   = {
                "answer_source":     result.answer_source.value,
                "finish_reason":     result.finish_reason.value,
                "confidence":        result.confidence,
                "process_completed": status == "SUCCESS",
                "conversation_id":   conversation_id,
                "msg_id":            msg_id,
            },
            metrics = {
                "latency_ms":    result.latency_ms,
                "model":         result.model,
                "input_tokens":  result.input_tokens,
                "output_tokens": result.output_tokens,
                "node_path":     result.node_path,
            },
            error = None if status == "SUCCESS" else "No valid upstream payload.",
        ),
    )