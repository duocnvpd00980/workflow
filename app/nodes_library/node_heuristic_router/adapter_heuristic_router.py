from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from .heuristic_router_service import HeuristicRouterService

_service = HeuristicRouterService()


async def node_heuristic_router(state: MainBus, config: RunnableConfig = None) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: HEURISTIC_ROUTER
    ======================================================================
    [BUSINESS INTENT]
    Bộ định tuyến zero-cost phân loại ý định người dùng bằng regex thuần.
    Không tốn một token LLM nào để quyết định luồng xử lý.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard - Kiểm tra reg_ig upstream. Nếu FAILED,
              hạ cánh an toàn lên Bus ngay.
    - Step 2: Context Extraction - Lấy sanitized query từ input_guard.payload.text.
    - Step 3: Pure Domain Execution - Gọi HeuristicRouterService phân loại route.
    - Step 4: Status Normalization & Bus Emit - Ghi route vào state.route
              để conditional edge của LangGraph đọc được.
    ======================================================================
    """

    # STEP 1: SAFE POST-GUARD
    error_message = None
    if not hasattr(state, "input_guard") or state.input_guard is None:
        error_message = (
            "[HEURISTIC_ROUTER] Topology Violation: input_guard không tồn tại trên Bus."
        )
    elif state.input_guard.payload.status != "SUCCESS":
        error_message = (
            f"[HEURISTIC_ROUTER] Upstream Failure: INPUT_GUARD thất bại. "
            f"Chi tiết: {state.input_guard.payload.error}"
        )

    if error_message:
        return StandardFrame.emit(
            registry_key=BusRegistry.RO,
            payload=BodyFrame(
                status="FAILED",
                text="Skipped due to upstream failure.",
                records=[],
                state={"process_completed": False, "route_to": "end"},
                context={"topology_error": error_message},
                error=error_message,
            ),
        )

    # STEP 2: CONTEXT EXTRACTION
    query = state.input_guard.payload.text

    # STEP 3: PURE DOMAIN EXECUTION
    result = _service.run(query=query)

    # STEP 4: STATUS NORMALIZATION & BUS EMIT
    return StandardFrame.emit(
        registry_key=BusRegistry.RO,
        payload=BodyFrame(
            status="SUCCESS",
            text=query,
            records=[],
            state={
                "process_completed": True,
                "route_to": result.route,
                "heuristic_router": result.route,
            },
            context={"matched_keyword": result.matched_keyword},
            error=None,
        ),
    )
