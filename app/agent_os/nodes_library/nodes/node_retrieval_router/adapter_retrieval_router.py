from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame

from .retrieval_router_protocol import RetrievalRouterInput
from .retrieval_router_service import RetrievalRouterService


async def node_RETRIEVAL_ROUTER(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:
    """
    ======================================================================
    INDUSTRIAL PROTOCOL WORKFLOW: [NODE_RETRIEVAL_ROUTER]
    ======================================================================
    """
    if isinstance(state, dict):
        state = MainBus.model_validate(state)

    upstream_policy = getattr(state, "reg_policy_engine", None)

    # ❌ CŨ: status="FAILURE"
    # ➔ ✅ MỚI: Sửa thành "FAILED" để khớp với luật Pydantic của MainBus
    if not upstream_policy or upstream_policy.payload.status != "SUCCESS":
        return StandardFrame.emit(
            registry_key=BusRegistry.RRO,
            payload=BodyFrame(
                status="FAILED",  # 🎯 Đã sửa ở đây
                text=getattr(state, "user_input", "") or "Bypass",
                state={"retrieval_needed": False},
                context={"source_node": "node_retrieval_router"},
                error="[RR] Control Plane gãy: reg_policy_engine trống hoặc báo lỗi.",
            ),
        )

    try:
        user_query = upstream_policy.payload.text

        router_input = RetrievalRouterInput(
            query=user_query,
            intent_context=upstream_policy.payload.state.get("route_to", "qa"),
        )

        service_result = await RetrievalRouterService.process_routing(router_input)

        return StandardFrame.emit(
            registry_key=BusRegistry.RRO,
            payload=BodyFrame(
                status="SUCCESS",  # Đúng chuẩn
                text=user_query,
                records=[],
                entities=[],
                state={
                    "route_to": "qa",
                    "retrieval_needed": service_result.retrieval_needed,
                    "rewritten_query": service_result.rewritten_query,
                    "search_namespaces": service_result.search_namespaces,
                },
                metrics={"confidence_score": service_result.confidence_score},
                context={
                    "source_node": "node_retrieval_router",
                    "pipeline": "rag_heavy_path",
                },
                error=None,
            ),
        )

    except Exception as runtime_err:
        return StandardFrame.emit(
            registry_key=BusRegistry.RRO,
            payload=BodyFrame(
                status="FAILED",  # 🎯 Đã sửa ở đây
                text=getattr(state, "user_input", ""),
                state={"retrieval_needed": False},
                context={"source_node": "node_retrieval_router"},
                error=f"[RR] Lỗi xử lý Runtime nội bộ: {str(runtime_err)}",
            ),
        )
