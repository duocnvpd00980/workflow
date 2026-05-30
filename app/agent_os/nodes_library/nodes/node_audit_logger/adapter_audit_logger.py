from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame

from .audit_logger_service import AuditLoggerService

# Khởi tạo Service Module duy nhất cấp module để tái sử dụng
audit_service = AuditLoggerService()

async def node_AUDIT_LOGGER(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [AUDIT_LOGGER]
    ======================================================================
    """

    # ==================================================================
    # STEP 1: SAFE POST-GUARD (HẠ CÁNH AN TOÀN - TRÁNH CRASH APP)
    # ==================================================================
    error_message = None
    
    # 🎯 FIX 1: Lấy đúng key đăng ký thực tế trên mạng Bus thay vì viết cứng chuỗi (thường là "node_reg_ui_selector")
    reg_ui_key = BusRegistry.UI  
    
    # Trích xuất an toàn đối tượng node UI Selector bằng getattr phòng vệ
    ui_node = getattr(state, reg_ui_key, None) if hasattr(state, reg_ui_key) else None

    # Tình huống 1: Node ui_selector hoàn toàn bị nhảy cóc hoặc chưa đăng ký thành công trên Bus
    if not ui_node or not hasattr(ui_node, "payload") or ui_node.payload is None:
        error_message = f"[AUDIT_LOGGER] Topology Violation: UI Selector Node ({reg_ui_key}) không tồn tại hoặc không có payload hợp lệ trên mạng Bus!"

    # Tình huống 2: Node ui_selector có tồn tại nhưng trạng thái tuyến trước đã thất bại
    elif ui_node.payload.status != "SUCCESS":
        error_message = f"[AUDIT_LOGGER] Upstream Failure: UI Selector Node liền trước gặp sự cố! Chi tiết: {getattr(ui_node.payload, 'error', 'Unknown Error')}"

    # NẾU PHÁT HIỆN VI PHẠM: Đóng gói trả về trạng thái FAILED trực tiếp lên Bus, không dùng 'raise'
    if error_message:
        return StandardFrame.emit(
            registry_key=BusRegistry.AL,  
            payload=BodyFrame(
                status="FAILED",
                text="Audit logging skipped or degraded due to upstream schema violation.",
                records=[],
                state={"process_completed": False},
                context={"topology_error": error_message},
                error=error_message
            )
        )

    # ==================================================================
    # STEP 2: CONTEXT EXTRACTION (CHỈ CHẠY KHI ĐỦ ĐIỀU KIỆN AN TOÀN)
    # ==================================================================
    # 🎯 FIX 2: Bóc tách an toàn thông qua biến ui_node đã qua vòng kiểm duyệt ở trên
    prev_payload = ui_node.payload
    
    # Phòng vệ chuỗi văn bản nếu text của tuyến trước bị None/Rỗng
    raw_text = prev_payload.text if prev_payload.text else "No output text provided"
    
    extracted_event_type = "workflow"
    extracted_actor = "system"
    extracted_action = f"pipeline_step_completed: {raw_text[:30]}..."
    extracted_success = True

    # ==================================================================
    # STEP 3: PURE DOMAIN EXECUTION
    # ==================================================================
    safe_output = await audit_service.write_log(
        event_type=extracted_event_type,
        actor=extracted_actor,
        action=extracted_action,
        success=extracted_success
    )
    
    payload_dict = safe_output.model_dump()

    # ==================================================================
    # STEP 4: STATUS NORMALIZATION & BUS EMIT
    # ==================================================================
    status = "SUCCESS" if payload_dict.get("success") else "FAILED"

    return StandardFrame.emit(
        registry_key=BusRegistry.AL,  
        payload=BodyFrame(
            status=status,
            text="Audit log recorded successfully.",
            records=[payload_dict],
            state={
                "event_type": payload_dict.get("event_type"),
                "actor": payload_dict.get("actor"),
                "action": payload_dict.get("action"),
            },
            context={
                "audit_raw": payload_dict,
            },
            error=None if status == "SUCCESS" else "Audit processing marked as failed."
        ),
    )