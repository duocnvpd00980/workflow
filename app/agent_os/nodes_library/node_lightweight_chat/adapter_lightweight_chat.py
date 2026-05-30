from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from agent_os.container import get_ctx
from .lightweight_chat_service import LightweightChatService

_service = LightweightChatService()


async def node_lightweight_chat(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:

    # =========================================================================
    # STEP 1 — SAFE POST-GUARD
    # =========================================================================
    supervisor = state.supervisor
    if not supervisor or not supervisor.payload:
        return StandardFrame.emit(
            registry_key=BusRegistry.LWC,
            payload=BodyFrame(
                status="FAILED",
                text="",
                error="[node_lightweight_chat] Supervisor frame missing.",
            ),
        )

    if supervisor.payload.status == "FAILED":
        return StandardFrame.emit(
            registry_key=BusRegistry.LWC,
            payload=BodyFrame(
                status="FAILED",
                text="",
                error=f"[node_lightweight_chat] Upstream failure: {supervisor.payload.error}",
            ),
        )

    if supervisor.payload.route != "smalltalk":
        return StandardFrame.emit(
            registry_key=BusRegistry.LWC,
            payload=BodyFrame(
                status="EMPTY",
                text="Skipped: not routed to smalltalk.",
            ),
        )

    # =========================================================================
    # STEP 2 — CONTEXT EXTRACTION & DI
    # =========================================================================
    user_input = state.input_guard.payload.text if state.input_guard else ""
    ctx        = await get_ctx()
    llm_engine = ctx.llm_factory.get_model("default")

    # =========================================================================
    # STEP 3 — PURE DOMAIN EXECUTION
    # =========================================================================
    try:
        result = await _service.run(
            user_input=user_input,
            llm_engine=llm_engine,
        )
        return StandardFrame.emit(
            registry_key=BusRegistry.LWC,
            payload=BodyFrame(
                status="SUCCESS",
                text=result.response,
                state={"process_completed": True},
                error=None,
            ),
        )

    except Exception as e:
        return StandardFrame.emit(
            registry_key=BusRegistry.LWC,
            payload=BodyFrame(
                status="FAILED",
                text="",
                error=f"[node_lightweight_chat] {e!r}",
            ),
        )