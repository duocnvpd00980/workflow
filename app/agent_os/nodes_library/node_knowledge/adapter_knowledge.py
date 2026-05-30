# ruff: noqa: E501
import logging
from langchain_core.runnables import RunnableConfig

from agent_os.nodes_library.node_knowledge.knowledge_service import (
    KnowledgeRetrieverService,
    KnowledgeService,
)
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from agent_os.container import AgentServices, get_ctx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_service = KnowledgeService()


async def node_knowledge(state: MainBus, config: RunnableConfig = None) -> dict:
    """
    CERTIFIED PROTOCOL WORKFLOW: [node_knowledge]
    Xử lý truy xuất RAG an toàn, đảm bảo biến đồng bộ và topology ổn định.
    """
    logger.info(
        "⚡ [GRAPH NODE] Tiến vào phân tầng truy xuất tri thức: [node_knowledge]"
    )

    if isinstance(state, dict):
        state = MainBus.model_validate(state)

    # STEP 1: SAFE POST-GUARD
    supervisor = getattr(state, BusRegistry.SV, None)
    error_message = None

    if not supervisor or not hasattr(supervisor, "payload"):
        error_message = (
            "[node_supervisor] Topology Violation: Upstream Supervisor missing."
        )
    elif supervisor.payload.status == "FAILED":
        error_message = (
            f"[node_supervisor] Upstream Failure: {supervisor.payload.error}"
        )
    elif getattr(supervisor.payload, "route", None) != "knowledge":
        return StandardFrame.emit(
            registry_key=BusRegistry.RS,
            payload=BodyFrame(
                status="EMPTY",
                text="Skipped: Routing bypass.",
                state={"retrieval_status": "SKIPPED"},
                context={"source": "node_knowledge"},
            ),
        )

    if error_message:
        return StandardFrame.emit(
            registry_key=BusRegistry.RS,
            payload=BodyFrame(
                status="FAILED",
                text="Skipped due to upstream failure.",
                error=error_message,
                context={"source": "node_knowledge"},
            ),
        )

    # STEP 2: CONTEXT EXTRACTION & DI
    ctx: AgentServices = await get_ctx()
    retrieval_svc = ctx.retrieval
    llm_engine = ctx.llm_factory.get_model("default")
    user_input = getattr(supervisor.payload, "text", "Câu hỏi chung")

    # STEP 3: PURE DOMAIN EXECUTION
    status = "SUCCESS"
    contexts_list = []
    top_k = 3
    score_threshold = 0.45

    try:
        search_query = await _service.run(user_input=user_input, llm_engine=llm_engine)

        payload = retrieval_svc.Request(query=search_query, top_k=top_k)
        db_result = await retrieval_svc.retrieve(payload)

        domain_service = KnowledgeRetrieverService(score_threshold=score_threshold)
        # Kiểm tra db_result an toàn
        raw_chunks = getattr(db_result, "chunks", []) if db_result else []
        result_dict = domain_service.process_retrieved_chunks(raw_chunks=raw_chunks)

        contexts_list = result_dict.get("contexts", [])
        status = "SUCCESS" if contexts_list else "EMPTY"

    except Exception as e:
        status = "FAILED"
        error_message = str(e)
        logger.error(f"[node_knowledge] Execution failed: {error_message}")

    # STEP 4: STATUS NORMALIZATION & BUS EMIT
    return StandardFrame.emit(
        registry_key=BusRegistry.RS,
        payload=BodyFrame(
            status=status,
            text=f"Retrieved {len(contexts_list)} chunks for: {user_input}",
            records=contexts_list,
            state={"query": user_input, "process_completed": True},
            metrics={"count": len(contexts_list), "score": score_threshold},
            context={"source": "node_knowledge", "pipeline": "rag_retrieval"},
            error=error_message,
        ),
    )
