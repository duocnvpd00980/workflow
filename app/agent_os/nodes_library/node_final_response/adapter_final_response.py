from __future__ import annotations
import logging
from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from .final_response_service import FinalResponseService

log = logging.getLogger(__name__)
_service = FinalResponseService()

async def node_final_response(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:
    """
    Node xử lý phản hồi cuối cùng sau khi bỏ Human Review.
    Nhận input từ LLM Generation hoặc Fallback Search.
    """
    
    # 1. Xác định nguồn input thay vì Human Review
    # Kiểm tra lần lượt các registry khả thi trong state
    upstream_payload = None
    flow_type = "chat" 
    
    # 1. KIỂM TRA ĐẦU VÀO TỪ CACHE (BƯỚC BỔ SUNG)
    if hasattr(state, "cache_read") and state.cache_read and state.cache_read.payload.route == "hit":
        upstream_payload = state.cache_read.payload
        flow_type = "cache"
        log.info("[node_final_response] Detected CACHE HIT")

    # 2. KIỂM TRA CÁC ĐẦU VÀO KHÁC (GIỮ NGUYÊN NHƯ CŨ)
    elif hasattr(state, "output_guard") and state.output_guard:
        upstream_payload = state.output_guard.payload
        flow_type = "knowledge"
    elif hasattr(state, "fallback_search") and state.fallback_search:
        upstream_payload = state.fallback_search.payload
        flow_type = "fallback"
    
    if not upstream_payload or upstream_payload.status != "SUCCESS":
        return _emit_error(
            text="Hệ thống không thể tạo phản hồi.",
            message="Không tìm thấy output hợp lệ từ LLM hoặc Fallback.",
            error_code="DATA_FLOW_EMPTY"
        )

    text = upstream_payload.text
    records = getattr(upstream_payload, "records", [])

    log.info("[node_final_response] Render flow=%s text_len=%d", flow_type, len(text))

    # 2. Render UI Components
    try:
        component_specs = _service.build_components(payload=upstream_payload, flow_type=flow_type)
        rendered = [spec.model_dump() for spec in component_specs]
    except Exception as exc:
        log.exception("[node_final_response] Rendering crash: %s", exc)
        return _emit_error(text=text, message="Lỗi render giao diện.", error_code="RENDER_CRASH", debug_details=str(exc))

    return StandardFrame.emit(
        registry_key=BusRegistry.FR,
        payload=BodyFrame(
            status="SUCCESS",
            text=text,
            records=rendered,
            state={"flow_type": flow_type, "ui_rendered": True},
            error=None,
        ),
    )

def _emit_error(*, text: str, message: str, error_code: str, debug_details: str = "") -> dict:
    return StandardFrame.emit(
        registry_key=BusRegistry.FR,
        payload=BodyFrame(
            status="FAILED",
            text=text,
            records=[{
                "component_id": "error_card",
                "props": {
                    "message": message,
                    "error_code": error_code,
                },
                "template_path": "widgets/error_display.html",
            }],
            error=f"[node_final_response] {message}",
        ),
    )