from langchain_core.runnables import RunnableConfig
from app.core.main_bus import MainBus
from app.core.registry  import BusRegistry
from app.core.protocol  import StandardFrame, BodyFrame

# Threshold cho RRF score (khác cosine similarity).
# RRF score = kết hợp thứ hạng BM25 + FAISS, range điển hình 0.01-0.05.
# > 0.02: tốt, 0.015-0.02: khá, < 0.015: kém.
RRF_THRESHOLD = 0.015

# Số chunks tối thiểu để coi là có đủ context.
# Nếu RRF thấp nhưng có nhiều chunks → vẫn cho qua (đa dạng nguồn).
MIN_CHUNKS = 2


async def node_relevance_check(state: MainBus, config: RunnableConfig = None) -> dict:
    """
    ======================================================================
    RELEVANCE_CHECK — Lọc kết quả RAG trước khi gọi LLM.
    ======================================================================
    Input:  knowledge_base payload (từ RAG search)
    Output: route="high_rel" → generation (đủ chất lượng)
            route="low_rel"  → fallback_search (không đủ)

    Logic:
        - FAILED/EMPTY ngay → low_rel
        - RRF score >= 0.015 OR chunks >= 2 → high_rel
        - Cả 2 đều fail → low_rel

    RRF score giải thích:
        Không phải cosine similarity. Là điểm kết hợp thứ hạng BM25 + FAISS.
        Range điển hình: 0.01-0.05. Score 0.03+ là rất tốt.
    ======================================================================
    """

    # ── STEP 1: POST-GUARD ────────────────────────────────────────────────
    kb = getattr(state, "knowledge_base", None)
    if not kb or not hasattr(kb, "payload"):
        return _emit_low_rel("Topology Violation: knowledge_base không tồn tại.")

    payload = kb.payload
    status = getattr(payload, "status", "FAILED")

    if status in ("FAILED", "EMPTY"):
        reason = getattr(payload, "error", "") or "No relevant chunks found."
        return _emit_low_rel(reason, context_text=getattr(payload, "text", ""))

    records = getattr(payload, "records", []) or []
    metrics = getattr(payload, "metrics", {}) or {}
    top_score = metrics.get("top_score", 0.0) or 0.0
    chunk_count = metrics.get("retrieved_chunks", 0)

    if not records:
        return _emit_low_rel(
            "Empty records.", context_text=getattr(payload, "text", "")
        )

    # ── STEP 2: DUAL THRESHOLD CHECK ──────────────────────────────────────
    # Cả 2 tiêu chí: RRF score cao HOẶC có nhiều chunks (đa dạng nguồn)
    score_ok = top_score >= RRF_THRESHOLD
    count_ok = chunk_count >= MIN_CHUNKS

    is_relevant = score_ok or count_ok

    # ── STEP 3: EMIT ──────────────────────────────────────────────────────
    query = ""
    state_dict = getattr(payload, "state", {}) or {}
    if isinstance(state_dict, dict):
        query = state_dict.get("query", "")

    if is_relevant:
        return StandardFrame.emit(
            registry_key=BusRegistry.RC,
            payload=BodyFrame(
                status="SUCCESS",
                route="high_rel",
                text=getattr(payload, "text", ""),
                records=records,
                state={
                    "process_completed": True,
                    "relevance_status": "high_rel",
                    "query": query,
                },
                metrics={
                    "top_score": top_score,
                    "rrf_threshold": RRF_THRESHOLD,
                    "retrieved_chunks": chunk_count,
                    "min_chunks": MIN_CHUNKS,
                    "score_passed": score_ok,
                    "count_passed": count_ok,
                },
                error=None,
            ),
        )

    # low_rel — cả 2 đều fail
    return _emit_low_rel(
        f"RRF {top_score:.3f} < {RRF_THRESHOLD} AND chunks {chunk_count} < {MIN_CHUNKS}",
        context_text=getattr(payload, "text", ""),
        records=records,
        top_score=top_score,
        chunk_count=chunk_count,
    )


def _emit_low_rel(
    reason: str,
    context_text: str = "",
    records: list = None,
    top_score: float = 0.0,
    chunk_count: int = 0,
) -> dict:
    return StandardFrame.emit(
        registry_key=BusRegistry.RC,
        payload=BodyFrame(
            status="SUCCESS",
            route="low_rel",
            text=context_text,
            records=records or [],
            state={
                "process_completed": False,
                "relevance_status": "low_rel",
            },
            metrics={
                "top_score": top_score,
                "rrf_threshold": RRF_THRESHOLD,
                "retrieved_chunks": chunk_count,
                "min_chunks": MIN_CHUNKS,
                "relevance_reason": reason,
            },
            error=None,
        ),
    )
