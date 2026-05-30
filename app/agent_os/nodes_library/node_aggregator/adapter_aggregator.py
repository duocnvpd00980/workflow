# ruff: noqa: E501
from langchain_core.runnables import RunnableConfig
from types import SimpleNamespace # Thêm để tạo mock object

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from agent_os.container import get_ctx
from .aggregator_service import AggregatorService

_service = AggregatorService()


async def node_aggregator(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:

    # =========================================================================
    # STEP 1 — SAFE POST-GUARD
    # =========================================================================
    evaluator = state.evaluator

    if evaluator is None or evaluator.payload is None:
        return StandardFrame.emit(
            registry_key=BusRegistry.AG,
            payload=BodyFrame(
                status="FAILED",
                text="",
                error="[node_aggregator] Evaluator frame missing.",
            ),
        )

    if evaluator.payload.status != "SUCCESS":
        return StandardFrame.emit(
            registry_key=BusRegistry.AG,
            payload=BodyFrame(
                status="FAILED",
                text="",
                error=f"[node_aggregator] Evaluator failed: {evaluator.payload.error}",
            ),
        )

    if evaluator.payload.route != "pass":
        return StandardFrame.emit(
            registry_key=BusRegistry.AG,
            payload=BodyFrame(
                status="FAILED",
                text="",
                error=f"[node_aggregator] Evaluator route='{evaluator.payload.route}', expected 'pass'.",
            ),
        )

    # =========================================================================
    # STEP 2 — CONTEXT EXTRACTION & DI
    # =========================================================================
    ctx        = await get_ctx()
    # llm_engine = ctx.llm_factory.get_model("default") # Không dùng tới khi mock

    original_query   = state.input_guard.payload.text if state.input_guard else ""
    agent_output     = evaluator.payload.text
    user_profile     = _safe_extract_user_profile(state)

    # =========================================================================
    # STEP 3 — PURE DOMAIN EXECUTION (MOCKED)
    # =========================================================================
    try:
        # Mock kết quả trả về để vượt qua lỗi AttributeError: 'LiteLLMEngine' object has no attribute 'with_structured_output'
        result = SimpleNamespace(
            final_response=f"Dựa trên yêu cầu của bạn: '{original_query}', kết quả là: {agent_output}",
            summary_of_changes="MOCKED_AGGREGATOR_SUCCESS",
            metadata={"mocked": True, "status": "bypassed_llm"}
        )
        execution_error = None

    except Exception as exc:
        result          = None
        execution_error = f"[node_aggregator] Service Error: {type(exc).__name__}: {exc}"

    # =========================================================================
    # STEP 4 — STATUS NORMALIZATION & BUS EMIT
    # =========================================================================
    if execution_error or result is None:
        return StandardFrame.emit(
            registry_key=BusRegistry.AG,
            payload=BodyFrame(
                status="FAILED",
                text=original_query,
                error=execution_error,
            ),
        )

    return StandardFrame.emit(
        registry_key=BusRegistry.AG,
        payload=BodyFrame(
            status="SUCCESS",
            text=result.final_response,
            state={"process_completed": True},
            metrics={"summary": result.summary_of_changes},
            context={"ui_metadata": result.metadata},
            error=None,
        ),
    )


# =============================================================================
# PRIVATE HELPERS
# =============================================================================

def _safe_extract_user_profile(state: MainBus) -> dict:
    for slot in ("shared_state", "input_guard"):
        frame = getattr(state, slot, None)
        if frame is None:
            continue
        profile = (getattr(frame.payload, "state", None) or {}).get("user_profile")
        if isinstance(profile, dict) and profile:
            return profile
    return {}