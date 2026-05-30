"""
adapter_supervisor.py
=====================
Mainboard Gatekeeper Layer — node_supervisor
Hạt nhân điều phối (Control Plane) của hệ thống Multi-Agent.
Bóc tách Bus, inject LLM, gọi Service và phát quyết định điều hướng lên mạng.
"""

from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from agent_os.container import get_ctx

from .supervisor_service import SupervisorService

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_service = SupervisorService()


# ---------------------------------------------------------------------------
# GATEKEEPER NODE
# ---------------------------------------------------------------------------
async def node_supervisor(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [node_supervisor]
    ======================================================================
    [BUSINESS INTENT]
    Đóng vai trò hạt nhân điều phối (Control Plane) của hệ thống Multi-Agent.
    Phân tích ngữ cảnh hội thoại, hồ sơ khách hàng, và lịch sử sửa lỗi để
    đưa ra quyết định lựa chọn Agent chuyên biệt kế tiếp kèm theo chỉ thị
    hành động chi tiết.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard       — Kiểm tra trạng thái an toàn của Node
                                      thượng nguồn (Input Guard hoặc Evaluator).
                                      Chuyển hóa lỗi hệ thống lên Bus thay vì
                                      crash ứng dụng.
    - Step 2: Context Extraction    — Trích xuất an toàn Profile khách hàng,
              & DI                    Episodic Memory từ Bus bằng toán tử chấm
                                      (.) và Inject High-IQ LLM Engine từ
                                      Container.
    - Step 3: Pure Domain Execution — Gọi SupervisorService, kích hoạt
                                      Structured Output trên LLM để thu về
                                      quyết định điều hướng Pydantic đóng băng.
    - Step 4: Status Normalization  — Đồng bộ hóa trạng thái 'next_action'
              & Bus Emit              phục vụ rẽ nhánh đồ thị và phát
                                      StandardFrame lên mạng Bus hệ thống.
    ======================================================================
    """

    # =========================================================================
    # STEP 1 — SAFE POST-GUARD (Chống crash hệ thống do đứt gãy topology)
    # =========================================================================
    # Supervisor nằm ở giao điểm của 2 luồng:
    #   - Luồng KHỞI ĐẦU  : thượng nguồn là INPUT_GUARD
    #   - Luồng SỬA LỖI   : thượng nguồn là EVALUATOR hoặc HUMAN_REVIEW
    # → Ưu tiên kiểm tra theo thứ tự: INPUT_GUARD → EVALUATOR → HUMAN_REVIEW

    upstream_frame = state.input_guard
    error_message = None

    # 1-A: Không tìm thấy bất kỳ Node thượng nguồn hợp lệ nào
    if upstream_frame is None:
        error_message = "[node_supervisor] Missing INPUT_GUARD upstream frame"

    elif getattr(upstream_frame.payload, "status", None) == "FAILED":
        error_message = "[node_supervisor] INPUT_GUARD FAILED: " + str(
            getattr(upstream_frame.payload, "error", None)
        )

    # --- Hạ cánh an toàn (Graceful Degradation) ----------------------------
    if error_message:
        return StandardFrame.emit(
            registry_key=BusRegistry.SV,
            payload=BodyFrame(
                status="FAILED",
                text="",
                records=[],
                entities=[],
                state={
                    "next_action": "end",
                    "process_completed": False,
                },
                metrics={"confidence_score": 0.0},
                context={"topology_error": error_message},
                error=error_message,
            ),
        )

    # =========================================================================
    # STEP 2 — CONTEXT EXTRACTION & DEPENDENCY INJECTION
    # =========================================================================
    ctx = await get_ctx()
    llm_engine = ctx.llm_factory.get_model("default")

    # --- Trích xuất lịch sử hội thoại ----------------------------------------
    history = _safe_extract_history(state)

    # --- Trích xuất User Profile ---------------------------------------------
    user_profile = _safe_extract_user_profile(state)

    # --- Trích xuất Episodic Memory từ Long-term Memory node -----------------
    relevant_episodes = _safe_extract_episodes(state)

    # --- Trích xuất evaluation_feedback (nếu đây là Correction Loop) ---------
    evaluation_feedback = _safe_extract_evaluation_feedback(state)

    # =========================================================================
    # STEP 3 — PURE DOMAIN EXECUTION
    # =========================================================================
    try:
        result = await _service.execute(
            user_input=state.input_guard.payload.text,
            history=history,
            user_profile=user_profile,
            relevant_episodes=relevant_episodes,
            evaluation_feedback=evaluation_feedback,
            llm_engine=llm_engine,
        )
        execution_error: str | None = None

    except Exception as exc:  # noqa: BLE001
        # Bắt toàn bộ lỗi LLM (timeout, schema mismatch, API error…)
        # TUYỆT ĐỐI không re-raise — tuân thủ Graceful Degradation Law
        result = None
        execution_error = (
            f"[node_supervisor] Service Execution Error: {type(exc).__name__}: {exc}"
        )

    # =========================================================================
    # STEP 4 — STATUS NORMALIZATION & BUS EMIT
    # =========================================================================
    if execution_error or result is None:
        return StandardFrame.emit(
            registry_key=BusRegistry.SV,
            payload=BodyFrame(
                status="FAILED",
                text="",
                records=[],
                entities=[],
                state={
                    "flow": "end",
                    "process_completed": False,
                },
                metrics={"confidence_score": 0.0},
                context={"execution_error": execution_error},
                error=execution_error,
            ),
        )

    # Thành công — phát quyết định điều hướng lên Bus
    return StandardFrame.emit(
        registry_key=BusRegistry.SV,
        payload=BodyFrame(
            status="SUCCESS",
            text=result.instruction,
            state={"process_completed": False},
            metrics={"confidence_score": result.confidence_score},
            context={"reasoning": result.reasoning},
            route=result.next_agent,
            error=None,
        ),
    ) | {"rework_count": state.rework_count + 1}


# =============================================================================
# PRIVATE HELPERS — Trích xuất an toàn, không bao giờ raise
# =============================================================================


def _safe_extract_history(state: MainBus) -> list:
    """
    Dò tìm lịch sử hội thoại từ Bus theo thứ tự ưu tiên.
    Trả về list rỗng nếu không tìm thấy.
    """
    for reg_attr in ("reg_history", "reg_session", "reg_input_guard"):
        frame = getattr(state, reg_attr, None)
        if frame is None:
            continue
        # Tìm trong state của payload (nơi phổ biến lưu history)
        payload_state = getattr(frame.payload, "state", None) or {}
        history = payload_state.get("history") or payload_state.get("conversation")
        if isinstance(history, list) and history:
            return history
        # Fallback: tìm trong context
        payload_ctx = getattr(frame.payload, "context", None) or {}
        history = payload_ctx.get("history")
        if isinstance(history, list) and history:
            return history
    return []


def _safe_extract_user_profile(state: MainBus) -> dict:
    """
    Trích xuất user_profile từ Bus theo thứ tự ưu tiên.
    Trả về dict rỗng nếu không tìm thấy.
    """
    for reg_attr in ("reg_user_profile", "reg_auth", "reg_session", "reg_input_guard"):
        frame = getattr(state, reg_attr, None)
        if frame is None:
            continue
        payload_state = getattr(frame.payload, "state", None) or {}
        profile = payload_state.get("user_profile") or payload_state.get("profile")
        if isinstance(profile, dict) and profile:
            return profile
        # Fallback: toàn bộ state nếu có vẻ là profile
        ctx = getattr(frame.payload, "context", None) or {}
        profile = ctx.get("user_profile")
        if isinstance(profile, dict) and profile:
            return profile
    return {}


def _safe_extract_episodes(state: MainBus) -> list:
    """
    Trích xuất Episodic Memory từ Long-term Memory node trên Bus.
    Trả về list rỗng nếu không tìm thấy.
    """
    for reg_attr in ("reg_memory", "reg_long_term_memory", "reg_episodic_memory"):
        frame = getattr(state, reg_attr, None)
        if frame is None:
            continue
        # Episodes thường nằm trong records hoặc state
        records = getattr(frame.payload, "records", None)
        if isinstance(records, list) and records:
            return records
        payload_state = getattr(frame.payload, "state", None) or {}
        episodes = payload_state.get("relevant_episodes") or payload_state.get(
            "episodes"
        )
        if isinstance(episodes, list) and episodes:
            return episodes
    return []


def _safe_extract_evaluation_feedback(state: MainBus) -> str:
    """
    Trích xuất evaluation_feedback từ Evaluator nếu đây là Correction Loop.
    Trả về chuỗi rỗng nếu không có (tức là lần chạy đầu tiên).
    """
    frame = getattr(state, "reg_evaluator", None)
    if frame is None:
        return ""

    # Feedback nằm trong error (khi Evaluator FAILED) hoặc context
    error_text = getattr(frame.payload, "error", None)
    if error_text:
        return str(error_text)

    ctx = getattr(frame.payload, "context", None) or {}
    feedback = ctx.get("feedback") or ctx.get("evaluation_feedback")
    if feedback:
        return str(feedback)

    return ""
