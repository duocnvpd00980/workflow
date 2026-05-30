# ruff: noqa: E501
from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from agent_os.container import get_ctx
from .lightweight_chat_service import LightweightChatService


async def node_LIGHTWEIGHT_CHAT(state: MainBus, config: RunnableConfig = None) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [LIGHTWEIGHT_CHAT]
    ======================================================================
    [BUSINESS INTENT]
    Tiếp nhận quyền hạn thi hành từ PolicyEngine và thực thi phản hồi hội thoại.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard - Kiểm tra 'reg_policy_engine' làm source of truth.
    - Step 2: Context Extraction & DI - Lấy input từ Classifier, lấy quyền hạn từ Policy.
    - Step 3: Pure Domain Execution - Gọi Service với các giới hạn (allow_knowledge=False).
    - Step 4: Status Normalization & Bus Emit - Đóng gói kết quả.
    ======================================================================
    """

    # STEP 1: SAFE POST-GUARD (Lắng nghe Policy Engine)
    error_message = None
    if not hasattr(state, "reg_policy_engine") or state.reg_policy_engine is None:
        error_message = (
            "[LIGHTWEIGHT_CHAT] Topology Violation: 'reg_policy_engine' missing!"
        )
    elif state.reg_policy_engine.payload.status != "SUCCESS":
        error_message = f"[LIGHTWEIGHT_CHAT] Upstream Failure: {state.reg_policy_engine.payload.error}"

    if error_message:
        return StandardFrame.emit(
            registry_key=BusRegistry.LWC,
            payload=BodyFrame(
                status="FAILED",
                text="Skipped due to upstream policy failure.",
                error=error_message,
            ),
        )

    # STEP 2: CONTEXT EXTRACTION & DEPENDENCY INJECTION
    # Lấy text thô từ Classifier (vẫn tồn tại trên Bus)
    user_brief = state.reg_intent_classifier.payload.text

    # Lấy cấu hình quyền hạn từ Policy Engine
    payload = state.reg_policy_engine.payload.context
    intent_context = {
        "tone_hint": payload.get("tone_hint", "friendly"),
        "fallback_activated": payload.get("fallback_activated", False),
    }

    ctx = await get_ctx()
    llm_engine = ctx.llm_factory.get_model("default")

    # STEP 3: PURE DOMAIN EXECUTION
    service_module = LightweightChatService(llm_engine=llm_engine)
    result = await service_module.run(
        user_input=str(user_brief), context=intent_context
    )

    # STEP 4: STATUS NORMALIZATION & BUS EMIT
    return StandardFrame.emit(
        registry_key=BusRegistry.LWC,
        payload=BodyFrame(
            status="SUCCESS",
            text=result.response,
            records=[result.response],
            entities=[],
            state={"tone": intent_context["tone_hint"], "process_completed": True},
            context={
                "engine_type": "default_llm",
                "policy_enforced": payload.get("intent_mode"),
            },
            error=None,
        ),
    )
