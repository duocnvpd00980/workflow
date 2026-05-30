import json
import traceback
from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from .ui_selector_service import UISelectorService

# Khởi tạo instance single của service xử lý logic giao diện phẳng
ui_service = UISelectorService()

async def node_UI_SELECTOR(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [UI_SELECTOR]
    ======================================================================
    [BUSINESS INTENT]
    Đọc dữ liệu phẳng, sạch từ node_FINALIZER thông qua thanh ghi BusRegistry.RF.
    Dùng Domain Service để kiểm tra dữ liệu thực tế, lựa chọn component phù hợp,
    ép kiểu nghiêm ngặt qua Pydantic Schema để tránh lỗi render ở tầng Frontend.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard — Kiểm tra sự hiện diện của node_FINALIZER (BusRegistry.RF).
    - Step 2: Context Extraction — Trích xuất thực thể BodyFrame nguyên bản bằng toán tử chấm.
    - Step 3: Pure Domain Execution — Giao dịch qua Service để định tuyến component và validate props.
    - Step 4: Status Normalization & Bus Emit — Đóng gói danh sách component đã render
              vào danh mục `records` phẳng và phát tán StandardFrame lên Bus.
    ======================================================================
    """
    print("\n" + "🛡️" * 25)
    print("🖥️ [ADAPTER_UI_SELECTOR] EXECUTING CERTIFIED PIPELINE WORKFLOW")
    print("🛡️" * 25)

    # Đảm bảo state được đồng bộ cấu trúc Pydantic MainBus
    if isinstance(state, dict):
        state = MainBus.model_validate(state)

    print(state)
    # ==================================================================
    # STEP 1: SAFE POST-GUARD (KIỂM TRA CHẶT CHẼ THƯỢNG NGUỒN)
    # ==================================================================
    finalizer_node = state.reg_finalizer if hasattr(state, "reg_finalizer") else None
    topology_error = None

    if not finalizer_node or finalizer_node.payload is None:
        topology_error = "[UI_SELECTOR] Topology Violation: Không tìm thấy payload từ node_FINALIZER (BusRegistry.RF) trên mạng Bus!"
    
    if topology_error:
        print(f"❌ {topology_error}")
        # Cứu hộ Topology: Phát thẳng lỗi cấu trúc hệ thống lên Bus để hạ cánh an toàn
        return StandardFrame.emit(
            registry_key=BusRegistry.UI,
            payload=BodyFrame(
                status="FAILED",
                text="Skipped component selection due to missing upstream context.",
                records=[{
                    "component_id": "error_card",
                    "props": {
                        "message": "Kiến trúc hệ thống bị đứt gãy, không tìm thấy kết quả từ node Finalizer.",
                        "title": "Lỗi luồng xử lý (Topology)",
                        "error_code": "TOPOLOGY_VIOLATION",
                        "failed_node": "node_UI_SELECTOR"
                    },
                    "template_path": "widgets/error_display.html"
                }],
                entities=[],
                state={"flow_type": "error", "ui_rendered": False},
                metrics={},
                context={"topology_error": topology_error},
                error=topology_error
            )
        )

    # ==================================================================
    # STEP 2: CONTEXT EXTRACTION (LẤY TRỰC TIẾP OBJECT PHẲNG QUA TOÁN TỬ CHẤM)
    # ==================================================================
    finalizer_payload: BodyFrame = finalizer_node.payload

    # ==================================================================
    # STEP 3: PURE DOMAIN EXECUTION (XỬ LÝ DỮ LIỆU SẠCH QUA SERVICE)
    # ==================================================================
    try:
        # 1. Phân tích dữ liệu thực tế từ Finalizer để chọn danh sách Component phù hợp
        selector_res = ui_service.select_components(finalizer_payload)
        
        # 2. Sinh cấu trúc UI cụ thể, tự điền các trường default và thực hiện ép kiểu nghiêm ngặt
        ui_output = ui_service.resolve_ui(
            selector_res=selector_res,
            finalizer_payload=finalizer_payload
        )

        # Chuyển đổi mảng Pydantic RenderedComponent thành danh sách dict thô an toàn
        rendered_components_list = [comp.model_dump() for comp in ui_output.rendered_components]

        print("\n✅ [UI_SELECTOR] COMPONENT SELECTION & VALIDATION SUCCESS:")
        print(json.dumps(rendered_components_list, indent=2, ensure_ascii=False))

        # ==================================================================
        # STEP 4: STATUS NORMALIZATION & BUS EMIT (TUÂN THỦ STRICT 8 FIELDS)
        # ==================================================================
        orig_state = finalizer_payload.state or {}
        
        # Đồng bộ và mở rộng thông tin state kiểm soát của hệ thống
        updated_state = {
            **orig_state,
            "ui_rendered": True,
            "selector_status": ui_output.selector_status,
            "fallback_used": ui_output.fallback_used
        }

        return StandardFrame.emit(
            registry_key=BusRegistry.UI,
            payload=BodyFrame(
                status=finalizer_payload.status,
                text=finalizer_payload.text,             # Giữ nguyên Single Source of Truth của tầng Content
                records=rendered_components_list,        # Đẩy TOÀN BỘ danh sách Component đã validate vào trường records phẳng!
                entities=finalizer_payload.entities or [],
                state=updated_state,
                metrics=finalizer_payload.metrics or {},
                context={
                    "summary_message": "UI component conversion finalized perfectly.",
                    "raw_text_fallback": ui_output.raw_text_fallback
                },
                error=finalizer_payload.error
            )
        )

    except Exception as ex:
        print("\n" + "💥" * 30)
        print("[UI_SELECTOR ADAPTER] CRITICAL UNHANDLED EXCEPTION IN PIPELINE EXECUTION")
        traceback.print_exc()
        print("💥" * 30 + "\n")

        # Cứu hộ khẩn cấp mức Runtime (Crash Protection tầng cuối cùng)
        emergency_component = [{
            "component_id": "error_card",
            "props": {
                "message": "Không thể xử lý hoặc hiển thị cấu trúc giao diện do xung đột logic nội bộ.",
                "title": "Lỗi runtime nghiêm trọng",
                "error_code": "UI_SELECTOR_ADAPTER_CRASH",
                "failed_node": "node_UI_SELECTOR",
                "debug_details": str(ex)
            },
            "template_path": "widgets/error_display.html"
        }]

        return StandardFrame.emit(
            registry_key=BusRegistry.UI,
            payload=BodyFrame(
                status="FAILED",
                text="UI rendering component pipeline crashed down completely.",
                records=emergency_component,
                entities=[],
                state={"flow_type": "error", "ui_rendered": False},
                metrics={},
                context={"exception_trace": str(ex)},
                error=str(ex)
            )
        )