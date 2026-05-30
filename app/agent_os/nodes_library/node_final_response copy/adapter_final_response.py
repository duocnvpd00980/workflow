# agent_os/nodes_library/node_final_response/adapter_final_response.py
"""
Node: node_final_response
─────────────────────────
Hai luồng vào (theo graph):
  ① node_human_review  → route="approved"  → flow = "knowledge" | "marketing"
  ② node_lightweight_chat                  → flow = "chat"
"""

from __future__ import annotations

import logging

from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from .final_response_service import FinalResponseService

log = logging.getLogger(__name__)

_service = FinalResponseService()


def _resolve_upstream(state: MainBus) -> tuple[str | None, list, str]:
    """
    Trả về (text, records, flow_type).

    node_human_review emit BodyFrame(route="approved" | "rejected").
    Chỉ tiếp nhận khi route == "approved".
    KHÔNG check payload.approved (field không tồn tại trên BodyFrame).
    """
    # ── Luồng chính: human_review approved ──────────────────────────────────
    hr = state.human_review
    if (
        hr
        and hr.payload
        and hr.payload.status == "SUCCESS"
        and hr.payload.route == "approved"          # ← khớp với node_human_review emit
    ):
        flow = "knowledge" if state.knowledge else "marketing"
        return hr.payload.text, hr.payload.records or [], flow

    # ── Luồng chat nhẹ ───────────────────────────────────────────────────────
    lc = state.lightweight_chat
    if lc and lc.payload and lc.payload.status == "SUCCESS":
        text = lc.payload.text
        # Đảm bảo records là một list rỗng [] nếu không có dữ liệu
        records = lc.payload.records or [] 
        return text, records, "chat"

    return None, [], "default"


async def node_final_response(
    state: MainBus,
    config: RunnableConfig = None,  # noqa: ARG001
) -> dict:

    text, records, flow_type = _resolve_upstream(state)

    if not text:
        log.error("[node_final_response] Upstream frame thiếu text hợp lệ.")
        return _emit_error(
            text="",
            message="Không tìm thấy output hợp lệ từ upstream node.",
            error_code="TOPOLOGY_VIOLATION",
        )

    log.debug("[node_final_response] flow=%s text_len=%d records=%d", flow_type, len(text), len(records))

    upstream = BodyFrame(
        status="SUCCESS",
        text=text,
        records=records,
        state={"flow_type": flow_type},
    )

    try:
        component_specs = _service.build_components(payload=upstream, flow_type=flow_type)
        rendered = [spec.model_dump() for spec in component_specs]
    except Exception as exc:
        log.exception("[node_final_response] FinalResponseService crash: %s", exc)
        return _emit_error(text=text, message="Lỗi render giao diện.", error_code="FINAL_RESPONSE_CRASH", debug_details=str(exc))

    return StandardFrame.emit(
        registry_key=BusRegistry.FR,
        payload=BodyFrame(
            status="SUCCESS",
            text=text,
            records=rendered,
            state={"flow_type": flow_type, "ui_rendered": True, "component_count": len(rendered)},
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
                    "title":        "Hệ thống thông báo",
                    "message":      message,
                    "error_code":   error_code,
                    "failed_node":  "node_final_response",
                    "debug_details": debug_details,
                },
                "template_path": "widgets/error_display.html",
            }],
            error=f"[node_final_response] {message}",
        ),
    )