import json
from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame

from .finalizer_service import FinalizerService

# Khởi tạo Service Module duy nhất cấp module
service_module = FinalizerService()

async def node_FINALIZER(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [FINALIZER]
    ======================================================================
    [BUSINESS INTENT]
    Hợp nhất và đóng gói dữ liệu đầu ra từ các luồng nghiệp vụ rẽ nhánh,
    chuẩn hóa cấu trúc gói tin PHẲNG để chuyển giao an toàn cho lớp UI Selector.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard - Xác thực cấu trúc Bus và kiểm tra tình trạng hoạt động của các luồng rẽ nhánh trước đó nhằm tránh crash đồ thị.
    - Step 2: Context Extraction - Trích xuất an toàn Object Payload (BodyFrame) của các luồng thông qua toán tử chấm (.). Không xả dict thô.
    - Step 3: Pure Domain Execution - Thực thi Service phân giải dữ liệu lõi, truyền trực tiếp các BodyFrame Object, nhận về FinalizerOutput đóng băng.
    - Step 4: Status Normalization & Bus Emit - Ánh xạ phẳng 1-1 dữ liệu từ tầng Service vào 8 trường hợp lệ của BodyFrame và phát StandardFrame.
    ======================================================================
    """
    print("\n" + "🏁" * 25)
    print("🛡️ [ADAPTER_FINALIZER] EXECUTING CERTIFIED PIPELINE WORKFLOW")
    print("🏁" * 25)

    if isinstance(state, dict):
        state = MainBus.model_validate(state)

    # ==================================================================
    # STEP 1: SAFE POST-GUARD (CHỐNG CRASH LUỒNG)
    # ==================================================================
    has_active_lane = any([
        getattr(state, "reg_dead_letter_queue", None),
        getattr(state, "reg_lightweight_chat", None),
        getattr(state, "reg_qa_response", None),
        getattr(state, "reg_ads", None),
        getattr(state, "reg_blog_writer", None),
        getattr(state, "reg_email", None)
    ])

    if not has_active_lane:
        error_msg = "[NODE_FINALIZER] Pipeline Broken: Toàn bộ các luồng xử lý trước đều không có dữ liệu."
        return StandardFrame.emit(
            registry_key=BusRegistry.RF,
            payload=BodyFrame(
                status="FAILED",
                text="Hệ thống không tìm thấy dữ liệu xử lý phù hợp.",
                records=[],
                entities=[],
                state={"flow_type": "error", "status": "FAILED"},
                metrics={"flow_type": "error"},
                context={"topology_error": error_msg},
                error=error_msg
            )
        )

    # ==================================================================
    # STEP 2: CONTEXT EXTRACTION (TRÍCH XUẤT OBJECT SẠCH - KHÔNG DUMP DICT)
    # ==================================================================
    dlq_payload = state.reg_dead_letter_queue.payload if getattr(state, "reg_dead_letter_queue", None) else None
    chat_payload = state.reg_lightweight_chat.payload if getattr(state, "reg_lightweight_chat", None) else None
    qa_payload = state.reg_qa_response.payload if getattr(state, "reg_qa_response", None) else None
    ads_payload = state.reg_ads.payload if getattr(state, "reg_ads", None) else None
    blog_payload = state.reg_blog_writer.payload if getattr(state, "reg_blog_writer", None) else None
    email_payload = state.reg_email.payload if getattr(state, "reg_email", None) else None

    # ==================================================================
    # STEP 3: PURE DOMAIN EXECUTION
    # ==================================================================
    # Truyền thẳng các Object Payload dạng BodyFrame vào Service xử lý
    result = await service_module.resolve(
        dlq=dlq_payload,
        chat=chat_payload,
        qa=qa_payload,
        ads=ads_payload,
        blog=blog_payload,
        email=email_payload
    )

    print("\n📦 FINALIZER COMPLIANT OUTPUT LOGGING FOR UI:")
    print(json.dumps({
        "status": result.status,
        "flow_type": result.flow_type,
        "text": result.text,
        "summary_message": result.summary_message
    }, indent=2, ensure_ascii=False))
    print("🏁" * 25 + "\n")

    # ==================================================================
    # STEP 4: STATUS NORMALIZATION & BUS EMIT (STRICT SCHEMAS)
    # ==================================================================
    # Tuyệt đối tuân thủ cấu trúc phẳng, đưa UI Output về đúng trường `text` gốc của BodyFrame.
    return StandardFrame.emit(
        registry_key=BusRegistry.RF,
        payload=BodyFrame(
            status=result.status,
            text=result.text,  # UI OUTPUT SINGLE SOURCE OF TRUTH PHẲNG
            records=[],
            entities=[],
            state={
                "flow_type": result.flow_type,
                "status": result.status,
            },
            metrics={
                "flow_type": result.flow_type
            },
            context={
                "summary_message": result.summary_message
            },
            error=result.error_details
        ),
    )