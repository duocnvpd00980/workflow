"""
=======================================================================
CERTIFIED PROTOCOL WORKFLOW: node_shared_state
=======================================================================
BUSINESS INTENT
  Đồng bộ và lưu trữ nội dung đã qua kiểm duyệt của con người vào kho trạng 
  thái dùng chung, đảm bảo tính nhất quán dữ liệu trước khi kết thúc luồng.

UPSTREAM DEPENDENCY
  Reads from : state.reg_human_review
  Emits to   : BusRegistry.SHARED_STATE

WORKFLOW PIPELINE
  S1 Safe Post-Guard         — Validate upstream. Emit FAILED, never raise.
  S2 Context Extraction & DI — Dot-notation extraction. get_ctx() injection.
  S3 Pure Domain Execution   — Service call. Receive frozen Pydantic Object.
  S4 Status Normalization    — Derive status. Emit single StandardFrame.
=======================================================================
"""



# Giả lập hàm get_ctx theo tiêu chuẩn Article 1.2
from agent_os.nodes_library.node_shared_state.shared_state_protocol import SharedStateOutput
from agent_os.nodes_library.node_shared_state.shared_state_service import SharedStateService
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.protocol import BodyFrame, StandardFrame
from agent_os.system.bus.registry import BusRegistry


async def get_ctx():
    class MockCtx:
        pass
    return MockCtx()

async def node_shared_state(state: MainBus) -> BodyFrame:
    # ───────────────────────────────────────────────────────────────────
    # S1 SAFE POST-GUARD
    # ───────────────────────────────────────────────────────────────────
    # Kiểm tra tính hợp lệ của bước kiểm duyệt con người ngay phía trước
    if state.reg_human_review is None or state.reg_human_review.status != "SUCCESS":
        return StandardFrame.emit(
            registry_key=BusRegistry.SHARED_STATE,
            payload=BodyFrame(
                status="FAILED",
                text="Lỗi đồng bộ: Không tìm thấy dữ liệu phê duyệt hợp lệ từ bước kiểm duyệt con người.",
                error="UPSTREAM_HUMAN_REVIEW_INVALID"
            )
        )

    # ───────────────────────────────────────────────────────────────────
    # S2 CONTEXT EXTRACTION & DEPENDENCY INJECTION
    # ───────────────────────────────────────────────────────────────────
    # Trích xuất nội dung văn bản cuối cùng bằng dot-notation thuần túy
    approved_text: str = state.reg_human_review.text
    ctx = await get_ctx()

    # ───────────────────────────────────────────────────────────────────
    # S3 PURE DOMAIN EXECUTION
    # ───────────────────────────────────────────────────────────────────
    # Gọi tầng nghiệp vụ để chuẩn hóa trạng thái lưu trữ
    domain_result: SharedStateOutput = await SharedStateService.synchronize_state(
        final_text=approved_text
    )

    # ───────────────────────────────────────────────────────────────────
    # S4 STATUS NORMALIZATION & EMIT
    # ───────────────────────────────────────────────────────────────────
    if not domain_result.is_synced:
        return StandardFrame.emit(
            registry_key=BusRegistry.SHARED_STATE,
            payload=BodyFrame(
                status="FAILED",
                text="Đồng bộ trạng thái thất bại do dữ liệu rỗng.",
                error="STATE_SYNC_EMPTY_PAYLOAD"
            )
        )

    # Ghi nhận thành công, chuyển tiếp văn bản sang node_final_response để xuất xưởng
    return StandardFrame.emit(
        registry_key=BusRegistry.SHARED_STATE,
        payload=BodyFrame(
            status="SUCCESS",
            text=domain_result.persisted_text,
            records=[],
            state={
                "synced": True,
                "updated_keys": domain_result.updated_keys
            }
        )
    )