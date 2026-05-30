# ruff: noqa: E501
import logging
from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from agent_os.container import get_ctx
from .intent_classifier_service import IntentClassifierService

logger = logging.getLogger(__name__)


async def node_INTENT_CLASSIFIER(state: MainBus, config: RunnableConfig = None) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [INTENT_CLASSIFIER]
    ======================================================================
    [BUSINESS INTENT]
    Phân loại ý định người dùng (Intent Classification) phục vụ điều hướng luồng nghiệp vụ.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard - Kiểm tra trạng thái của reg_gatekeeper để đảm bảo đầu vào an toàn.
    - Step 2: Context Extraction & DI - Khai thác dữ liệu từ Bus và khởi tạo dịch vụ từ Container.
    - Step 3: Pure Domain Execution - Gọi service thực thi phân loại qua 3 tầng (Fast-Path/Router/LLM).
    - Step 4: Status Normalization & Bus Emit - Đóng gói kết quả vào BodyFrame (tuân thủ schema nghiêm ngặt).
    ======================================================================
    """

    # STEP 1: SAFE POST-GUARD (CHỐNG CRASH HỆ THỐNG)
    error_message = None
    if not hasattr(state, "reg_gatekeeper") or state.reg_gatekeeper is None:
        error_message = "[INTENT_CLASSIFIER] Topology Violation: 'reg_gatekeeper' không tồn tại trên Bus!"
    elif state.reg_gatekeeper.payload.status != "SUCCESS":
        error_message = f"[INTENT_CLASSIFIER] Upstream Failure: Gatekeeper thất bại! Chi tiết: {state.reg_gatekeeper.payload.error}"

    if error_message:
        return StandardFrame.emit(
            registry_key=BusRegistry.IC,
            payload=BodyFrame(
                status="FAILED",
                text="Skipped due to upstream failure.",
                records=[],
                entities=[],
                state={"process_completed": False},
                context={"topology_error": error_message},
                error=error_message,
            ),
        )

    # STEP 2: CONTEXT EXTRACTION & DEPENDENCY INJECTION
    rewrite_prompt = state.reg_gatekeeper.payload.text
    ctx = await get_ctx()
    service = IntentClassifierService(
        ollama_embed_model=ctx.llm_factory.get_embedding("default_embed"),
        llm_engine=ctx.llm_factory.get_model("default"),
    )

    # STEP 3: PURE DOMAIN EXECUTION
    error_log = None
    try:
        result = await service.run_classification(user_text=str(rewrite_prompt))
        intent = "qa" if result.mode == "error" else result.mode
        confidence = 0.50 if result.mode == "error" else result.confidence
    except Exception as e:
        error_log = str(e)
        logger.error("[INTENT_CLASSIFIER] Fallback activated due to: %s", error_log)
        intent, confidence = "qa", 0.45

    # STEP 4: STATUS NORMALIZATION & BUS EMIT
    return StandardFrame.emit(
        registry_key=BusRegistry.IC,
        payload=BodyFrame(
            status="SUCCESS",
            text=rewrite_prompt,  # Nội dung thô để Chat render prompt
            entities=[
                {
                    "intent": intent,
                    "confidence": confidence,
                }  # Đủ dữ liệu để Chat chọn Tone
            ],
            records=[{"label": intent, "score": confidence}],
            state={
                "intent": intent,  # Key chính cho node Chat logic
                "route_to": intent,
                "routing_ready": True,
                "tone_hint": "professional"
                if intent == "qa"
                else "friendly",  # Gợi ý tone cho Chat
            },
            metrics={"confidence": confidence},
            context={
                "original_input": rewrite_prompt,
                "tone_hint": "professional" if intent == "qa" else "friendly",
                "fallback_activated": error_log is not None,
                "internal_error": error_log,
                "is_knowledge_required": intent
                in ["qa", "marketing"],  # Gợi ý node Chat có nên gọi RAG không
            },
            error=None,
        ),
    )
