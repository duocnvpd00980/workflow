from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame

from .observer_service import ObserverService

observer_service = ObserverService()


async def node_OBSERVER(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:
    """
    OBSERVER NODE - FINAL SYSTEM MONITORING LAYER
    """

    # =========================================================
    # STEP 1: SAFE POST-GUARD (NO CRASH DESIGN)
    # =========================================================
    is_upstream_missing = False
    error_detail = None

    audit_node = getattr(state, "reg_qa_response", None)

    if audit_node is None or getattr(audit_node, "payload", None) is None:
        is_upstream_missing = True
        error_detail = "[OBSERVER] Topology Warning: QA/Audit node missing from Bus!"

    # =========================================================
    # STEP 2: DOMAIN EXECUTION
    # =========================================================
    payload = await observer_service.summarize(state=state)
    payload_dict = payload.model_dump()

    # =========================================================
    # STEP 3: STATUS NORMALIZATION
    # =========================================================
    if is_upstream_missing:
        status = "FAILED"
        system_health = "critical"
        error_msg = error_detail
    else:
        status = "SUCCESS"
        system_health = payload_dict.get("system_health", "healthy")

        # safe check upstream status
        try:
            upstream_status = audit_node.payload.status
            error_msg = (
                None if upstream_status == "SUCCESS" else "Upstream anomalies detected"
            )
        except Exception:
            error_msg = "Upstream status unavailable"

    # =========================================================
    # STEP 4: SAFE EXTRACTION
    # =========================================================
    quality_check = payload_dict.get("quality_check") or {}
    usage_stats = payload_dict.get("usage_stats") or {}

    body = BodyFrame(
        status=status,
        text=(
            "System observation completed smoothly."
            if status == "SUCCESS"
            else "System observation finished with alerts."
        ),
        records=[payload_dict],
        state={
            "current_step": payload_dict.get("current_step", "UNKNOWN"),
            "system_health": system_health,
        },
        metrics={
            "format_valid": quality_check.get("format_valid", False),
            "policy_violation": quality_check.get("policy_violation", False),
        },
        context={
            "usage_stats": usage_stats,
        },
        error=error_msg,
    )

    # =========================================================
    # STEP 5: EMIT TO BUS
    # =========================================================
    return StandardFrame.emit(
        registry_key=BusRegistry.OBS,
        payload=body,
    )
