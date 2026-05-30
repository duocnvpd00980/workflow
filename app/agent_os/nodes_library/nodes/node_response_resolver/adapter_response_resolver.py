# =========================================================
# FILE: adapter_response_resolver.py
# =========================================================
from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import (
    StandardFrame,
    BodyFrame,
)
from agent_os.container import get_ctx
from .response_resolver_service import ResponseResolverService

service_module = ResponseResolverService()


async def node_RESPONSE_RESOLVER(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [NODE_RESPONSE_RESOLVER]
    ======================================================================
    [BUSINESS INTENT]
    Phân tích ý định người dùng dựa trên dữ liệu đã làm sạch từ Intent Classifier
    để quyết định bẻ luồng sang nhánh RAG Retriever hoặc Trả lời trực tiếp.

    [WORKFLOW PIPELINE]
    - Step 1: Data Insurance - Đảm bảo dữ liệu đầu vào luôn là Object MainBus xịn.
    - Step 2: Fail-Fast Post-Guard - Kiểm duyệt an toàn từ NODE LIỀN TRƯỚC (Intent Classifier).
    - Step 3: Context Extraction & DI - Lấy ngữ cảnh sạch từ IC, nạp Cloud Router Engine.
    - Step 4: Pure Domain Execution - Thực thi gọi Service định tuyến.
    - Step 5: Status Normalization & Bus Emit - Phát StandardFrame kết quả lên Bus.
    ======================================================================
    """
    # STEP 1: DATA INSURANCE
    if isinstance(state, dict):
        state = MainBus.model_validate(state)

    # STEP 2: FAIL-FAST POST-GUARD (Sửa đổi: Đổi từ reg_seed thành reg_intent_classifier)
    if not state.reg_intent_classifier or state.reg_intent_classifier.payload.status != "SUCCESS":
        raise RuntimeError(
            "[NODE_RESPONSE_RESOLVER] Security Violation: Thanh ghi 'reg_intent_classifier' trống hoặc thất bại! Không thể định tuyến."
        )

    # STEP 3: CONTEXT EXTRACTION & DEPENDENCY INJECTION
    ctx = await get_ctx()
    cloud_engine = ctx.llm_factory.get_model()
    
    # ĐÚNG BẢN CHẤT: Lấy text gốc và context động từ kết quả của Intent Classifier
    user_query = state.user_input or state.reg_intent_classifier.payload.text or "Hi"
    
    # Lấy thông tin trạng thái/ngữ cảnh được trích xuất từ các bước trước để làm context cho LLM Resolver
    routing_context = state.reg_intent_classifier.payload.state

    # STEP 4: PURE DOMAIN EXECUTION
    result = await service_module.classify_intent(
        user_input=str(user_query),
        context=routing_context, # Nạp ngữ cảnh an toàn, đúng luồng mạch vẽ
        llm_engine=cloud_engine
    )

    intent = result.route or "invalid"
    
    # Map nhánh chạy thực tế khớp hoàn toàn với sơ đồ đồ thị bên dưới của bạn
    mapping = {
        "qa": ["retriever", "qa_response"],      
        "direct_qa": ["direct_qa_response"],      
        "invalid": [],                            
    }
    active_branches = mapping.get(intent, [])
    
    print(f"🤖 [NODE_RESPONSE_RESOLVER] Route: {intent} | Branches: {active_branches}")

    # STEP 5: STATUS NORMALIZATION & BUS EMIT
    policy_passed = (intent != "invalid")
    status = "SUCCESS" if policy_passed else "FAILED"

    return StandardFrame.emit(
        registry_key=BusRegistry.RR,
        payload=BodyFrame(
            status=status,
            text=user_query,
            state={
                "route_to": intent,
                "active_branches": active_branches,
                "reasoning": result.reasoning,
                "next_steps": result.next_steps,
            },
            metrics={
                "confidence_score": result.confidence_score,
            },
            error=None if policy_passed else "Response Resolver bẻ luồng thất bại: Hướng đi không hợp lệ."
        ),
    )