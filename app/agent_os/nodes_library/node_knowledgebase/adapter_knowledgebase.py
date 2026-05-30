from langchain_core.runnables import RunnableConfig
from agent_os.rag.rag_service import RAG
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame

_rag = RAG()


async def node_knowledgebase(
    state: MainBus,
    config: RunnableConfig = None
) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: KNOWLEDGE_BASE (RAG ZERO v2.1)
    ======================================================================
    """

    # ── STEP 1: POST-GUARD ────────────────────────────────────────────────
    cr = getattr(state, "cache_read", None)
    if not cr or not hasattr(cr, 'payload'):
        return _emit_failed("Topology Violation: cache_read không tồn tại.")

    payload = cr.payload
    if getattr(payload, "status", None) != "SUCCESS":
        return _emit_failed(getattr(payload, "error", "Upstream failed"))
    if getattr(payload, "route", None) != "miss":
        return _emit_failed("Invalid route: expected 'miss'")

    # ── STEP 2: EXTRACT QUERY ─────────────────────────────────────────────
    query = getattr(payload, "text", "")
    if not query:
        state_dict = getattr(payload, "state", {}) or {}
        if isinstance(state_dict, dict):
            query = state_dict.get("query", "")

    if not query:
        return _emit_failed("Empty query")

    # ── STEP 3: RAG SEARCH ────────────────────────────────────────────────
    try:
        rag_result = await _rag.search(query, top_k=3)
    except Exception as e:
        return _emit_failed(f"RAG search failed: {e}", rag_error=str(e))

    # ── STEP 4: EMIT ──────────────────────────────────────────────────────
    chunks = rag_result.chunks
    if not chunks:
        return StandardFrame.emit(
            registry_key=BusRegistry.KLB,
            payload=BodyFrame(
                status="EMPTY",
                text="Không tìm thấy thông tin liên quan.",
                records=[],
                state={"process_completed": True, "query": query, "node_count": 0},
                metrics={"retrieved_chunks": 0},
                error=None,
            )
        )

    context = "\n\n".join(f"[{i+1}] {c.text}" for i, c in enumerate(chunks))
    records = [{"text": c.text, "score": c.score, "meta": c.meta} for c in chunks]

    return StandardFrame.emit(
        registry_key=BusRegistry.KLB,
        payload=BodyFrame(
            status="SUCCESS",
            text=context,
            records=records,
            state={
                "process_completed": True,
                "query": query,
                "node_count": len(chunks),
                "source": rag_result.source,
            },
            metrics={
                "top_score": chunks[0].score,
                "retrieved_chunks": len(chunks),
            },
            error=None,
        )
    )


def _emit_failed(error: str, **context) -> dict:
    return StandardFrame.emit(
        registry_key=BusRegistry.KLB,
        payload=BodyFrame(
            status="FAILED",
            text="",
            records=[],
            state={"process_completed": False},
            context={"error": error, **context},
            error=error,
        )
    )