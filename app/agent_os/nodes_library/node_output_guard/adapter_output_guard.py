# adapter_output_guard.py
from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame

from .output_guard_service import OutputGuardService

_service = OutputGuardService()


async def node_output_guard(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:

    # =========================================================================
    # STEP 1 — SAFE POST-GUARD
    # =========================================================================
    generation = state.generation

    if generation is None or generation.payload is None:
        return StandardFrame.emit(
            registry_key=BusRegistry.OG,
            payload=BodyFrame(
                status="FAILED",
                text="",
                route="skip_cache",
                error="[node_output_guard] aggregator frame missing.",
            ),
        )

    if generation.payload.status != "SUCCESS":
        return StandardFrame.emit(
            registry_key=BusRegistry.OG,
            payload=BodyFrame(
                status="FAILED",
                route="skip_cache",
                text="",
                error=f"[node_output_guard] aggregator failed: {generation.payload.error}",
            ),
        )

    # =========================================================================
    # STEP 2 — PURE DOMAIN EXECUTION (rule-based, no LLM)
    # =========================================================================
    text = generation.payload.text
    result = _service.check(text)

    # =========================================================================
    # STEP 3 — BUS EMIT
    # =========================================================================
    if not result.is_safe:
        return StandardFrame.emit(
            registry_key=BusRegistry.OG,
            payload=BodyFrame(
                status="FAILED",
                route="skip_cache",
                text=text,
                error=f"[node_output_guard] {result.reason}",
                context={"violation": result.violation},
            ),
        )

    return StandardFrame.emit(
        registry_key=BusRegistry.OG,
        payload=BodyFrame(
            status="SUCCESS",
            route="cache",
            text=text,
            context={"violation": "none"},
            error=None,
        ),
    )
