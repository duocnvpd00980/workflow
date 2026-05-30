# ruff: noqa: E501
# /app/agent_os/graph/nodes/adapter_qa_retriever.py
import logging
from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from agent_os.container import AgentServices, get_ctx
from .qa_retriever_service import QARetrieverService, HyDEService

logger = logging.getLogger(__name__)


async def node_QA_RETRIEVER(
    state: MainBus,
    config: RunnableConfig = None
) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [QA_RETRIEVER]
    ======================================================================
    [VAI TRÒ]: Tiếp nhận tín hiệu định tuyến từ Retrieval Router (RR).
    Điều phối luồng: Inject LLM vào HyDEService để làm sạch/mở rộng query,
    gọi retrieval_svc quét Vector DB, và nén dữ liệu qua QARetrieverService.
    ======================================================================
    """
    logger.info("⚡ [GRAPH NODE] Tiến vào phân tầng truy xuất tri thức: [QA_RETRIEVER]")
    
    # ==================================================================
    # STEP 1: SAFE POST-GUARD (CHỐNG SẬP ĐỒ THỊ DO ĐỨT GÃY TOPOLOGY)
    # ==================================================================
    error_message = None
    resolver_property = BusRegistry.RRO
    
    resolver_node = getattr(state, resolver_property, None)
    if not resolver_node and isinstance(state, dict):
        resolver_node = state.get(resolver_property) or state.get("reg_response_resolver")

    if not resolver_node or not hasattr(resolver_node, "payload") or resolver_node.payload is None:
        error_message = f"[QA_RETRIEVER] Topology Violation: Thuộc tính định tuyến ({resolver_property}) không tồn tại trên mạng Bus!"
    elif resolver_node.payload.status == "FAILED":
        error_message = f"[QA_RETRIEVER] Upstream Failure: Node định tuyến liền trước (RR) gặp sự cố! Chi tiết: {resolver_node.payload.error}"

    if error_message:
        return StandardFrame.emit(
            registry_key=BusRegistry.QAR,
            payload=BodyFrame(
                status="FAILED",
                text="QA Retriever execution aborted due to upstream topology failure.",
                records=[],
                entities=[],
                state={"retrieval_status": "FAILED"},
                metrics={"count": 0, "top_k": 0, "score_threshold": 0.45},
                context={"topology_error": error_message},
                error=error_message
            )
        )

    resolver_state = getattr(resolver_node.payload, "state", {}) or {}
    if not isinstance(resolver_state, dict):
        resolver_state = {}
        
    retrieval_needed = resolver_state.get("retrieval_needed", True)

    brief = (
        resolver_state.get("rewritten_query") 
        or resolver_node.payload.text 
        or (state.get("user_input", "Hi") if isinstance(state, dict) else getattr(state, "user_input", "Hi"))
    )

    if not retrieval_needed:
        return StandardFrame.emit(
            registry_key=BusRegistry.QAR,
            payload=BodyFrame(
                status="SUCCESS",
                text=f"QA Retriever skipped gracefully: Retrieval not needed for query '{brief}'",
                records=[],
                entities=[],
                state={"query": brief, "retrieval_status": "SKIPPED"},
                metrics={"count": 0, "top_k": 0, "score_threshold": 0.45},
                context={"source": "node_qa_retriever", "pipeline": "rag_skip"},
                error=None
            )
        )

    # ==================================================================
    # STEP 2: DEPENDENCY INJECTION (DI) THEO CHUẨN PLUG-AND-PLAY
    # ==================================================================
    ctx: AgentServices = await get_ctx()
    retrieval_svc = ctx.retrieval
    llm_engine = ctx.llm_factory.get_model("default")

    # ==================================================================
    # STEP 3: PURE DOMAIN EXECUTION (Xử lý tuần tự qua các Domain Component)
    # ==================================================================
    top_k = 3
    raw_chunks = []
    status = "SUCCESS"
    error_message = None

    if retrieval_svc and llm_engine:
        try:
            # 1. Khởi tạo HyDEService độc lập và inject engine vào giống hệt luồng sinh Ads
            hyde_component = HyDEService(llm_engine=llm_engine)
            search_query = await hyde_component.run(query=brief)

            # 2. Phát lệnh tìm kiếm bằng chuỗi query tĩnh đã được tối ưu
            payload = retrieval_svc.Request(
                query=search_query,
                top_k=top_k,
            )
            db_result = await retrieval_svc.retrieve(payload)
            raw_chunks = db_result.chunks if db_result else []
        except Exception as err:
            status = "FAILED"
            error_message = str(err)
    else:
        status = "FAILED"
        error_message = "Dependency Injection Error: Retrieval Service or LLM Engine unavailable"

    contexts_list = []
    score_threshold = 0.45

    # 3. Sử dụng Domain Service chuyên trách để tinh lọc và đóng gói record phẳng
    if status != "FAILED":
        domain_service = QARetrieverService(score_threshold=score_threshold)
        result_dict = domain_service.process_retrieved_chunks(raw_chunks=raw_chunks)

        contexts_list = result_dict.get("contexts", [])
        score_threshold = result_dict.get("score_threshold", 0.45)

        if not contexts_list:
            status = "EMPTY"

    # ==================================================================
    # STEP 4: STATUS NORMALIZATION & BUS EMIT
    # ==================================================================
    return StandardFrame.emit(
        registry_key=BusRegistry.QAR,
        payload=BodyFrame(
            status=status,
            text=f"QA Retriever completed for query: '{brief}'",
            records=contexts_list,
            entities=[],
            state={
                "query": brief,
                "retrieval_status": status,
            },
            metrics={
                "count": len(contexts_list),
                "top_k": top_k,
                "score_threshold": score_threshold,
            },
            context={
                "source": "node_qa_retriever",
                "pipeline": "rag_retrieval",
            },
            error=error_message,
        ),
    )