# ruff: noqa: E501
import logging
from langchain_core.runnables import RunnableConfig
from agent_os.container import AgentServices, get_ctx
from agent_os.nodes_library.node_marketing.node_marketing_protocol import MarketingOutput
from agent_os.nodes_library.node_marketing.node_marketing_service import MarketingService
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.protocol import BodyFrame, StandardFrame
from agent_os.system.bus.registry import BusRegistry

logger = logging.getLogger(__name__)

async def node_marketing(
    state: MainBus, 
    config: RunnableConfig = None
) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [node_marketing]
    ======================================================================
    [BUSINESS INTENT]
    Tiếp nhận yêu cầu từ Supervisor để chuyển hóa thành nội dung tiếp thị 
    sáng tạo (Ads/Email/Social Copy) đáp ứng Brand Voice quy định.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard - Validate trạng thái từ Supervisor, xử lý 
      bỏ qua hoặc báo lỗi an toàn thay vì crash.
    - Step 2: Context Extraction & DI - Trích xuất yêu cầu gốc từ payload, 
      Inject Engine từ Container.
    - Step 3: Pure Domain Execution - Gọi MarketingService nhận kết quả bất biến.
    - Step 4: Status Normalization & Bus Emit - Đóng gói vào BodyFrame chuẩn 
      để phục vụ quá trình thẩm định của node_evaluator.
    ======================================================================
    """
    
    # ───────────────────────────────────────────────────────────────────
    # S1 SAFE POST-GUARD
    # ───────────────────────────────────────────────────────────────────
    resolver_node = getattr(state, BusRegistry.SV, None)
    error_message = None

    
    if not resolver_node or not hasattr(resolver_node, "payload"):
        error_message = "[node_marketing] Topology Violation: Upstream Supervisor missing."
    elif resolver_node.payload.status == "FAILED":
        error_message = f"[node_marketing] Upstream Failure: {resolver_node.payload.error}"
    elif resolver_node.payload.state.get("next_action") != "marketing":
        return StandardFrame.emit(
            registry_key=BusRegistry.RS,
            payload=BodyFrame(status="EMPTY", text="Skipped: Not target agent.", state={"process_completed": False})
        )

    if error_message:
        return StandardFrame.emit(
            registry_key=BusRegistry.RS,
            payload=BodyFrame(status="FAILED", text="Skipped due to upstream failure.", error=error_message)
        )

    # ───────────────────────────────────────────────────────────────────
    # S2 CONTEXT EXTRACTION & DEPENDENCY INJECTION
    # ───────────────────────────────────────────────────────────────────
    ctx: AgentServices = await get_ctx()
    input_text = resolver_node.payload.text
    
    # ───────────────────────────────────────────────────────────────────
    # S3 PURE DOMAIN EXECUTION
    # ───────────────────────────────────────────────────────────────────
    status = "SUCCESS"
    domain_result: MarketingOutput = None
    try:
        # Giả định Service đã được thiết kế trả về MarketingOutput (Pydantic model)
        domain_service = MarketingService(llm_engine=ctx.llm_factory.get_model("default"))
        domain_result = await domain_service.generate_marketing_content(sanitized_input=input_text)
    except Exception as e:
        status = "FAILED"
        error_message = str(e)

    # ───────────────────────────────────────────────────────────────────
    # S4 STATUS NORMALIZATION & EMIT
    # ───────────────────────────────────────────────────────────────────
    return StandardFrame.emit(
        registry_key=BusRegistry.RS,
        payload=BodyFrame(
            status=status,
            text=domain_result.campaign_copy if domain_result else "",
            records=[],
            state={"audience": domain_result.target_audience if domain_result else None, "process_completed": True},
            metrics={"tone": domain_result.tone_of_voice if domain_result else None},
            context={"source": "node_marketing", "pipeline": "creative_content"},
            error=error_message
        )
    )