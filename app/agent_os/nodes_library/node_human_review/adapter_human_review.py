# nodes_library/node_human_review/adapter_human_review.py

from __future__ import annotations
import logging
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame

log = logging.getLogger(__name__)


async def node_human_review(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:
    """
    Human-in-the-loop checkpoint dùng LangGraph interrupt().

    Vòng đời:
      Lần 1  → check guard → interrupt() → [graph dừng, đợi người dùng]
      Resume → node chạy lại từ đầu → check guard (idempotent) → interrupt()
               → nhận Command(resume=...) → xử lý decision → return frame
    """

    # ─── 1. Guard check ───────────────────────────────────────────────────────
    # IDEMPOTENT: chỉ đọc state, không có side-effect.
    # Chạy lại nhiều lần khi resume là an toàn.
    output_guard = state.output_guard

    if (
        output_guard is None
        or output_guard.payload is None
        or output_guard.payload.status != "SUCCESS"
    ):
        error_msg = (
            getattr(output_guard.payload, "error", "unknown")
            if output_guard and output_guard.payload
            else "No output_guard data"
        )
        log.error("[node_human_review] Guard failed — aborting: %s", error_msg)
        return StandardFrame.emit(
            registry_key=BusRegistry.HR,
            payload=BodyFrame(
                status="FAILED",
                text="",
                route="rejected",
                error=f"[node_human_review] Guard failed: {error_msg}",
            ),
        )

    draft: str = output_guard.payload.text or ""

    # ─── 2. Interrupt ─────────────────────────────────────────────────────────
    # KHÔNG bọc trong try/except — interrupt() hoạt động bằng cách raise exception
    # nội bộ. Bắt nó sẽ phá vỡ cơ chế dừng của LangGraph.
    #
    # Payload phải JSON-serializable (str, dict với value đơn giản).
    # Giá trị này xuất hiện trong chunk["__interrupt__"][0].value khi streaming.
    log.info("[node_human_review] Triggering interrupt — awaiting human decision")

    decision: dict = interrupt({
        "draft": draft,
        "instruction": (
            "Review nội dung. "
            "Resume với {'action': 'approved'|'rejected', 'feedback': '...'}"
        ),
    })

    # ─── 3. Xử lý decision (chỉ chạy sau Command(resume=...)) ───────────────
    # Docs: "The node restarts from the beginning when resumed" —
    # đoạn code dưới đây chỉ được thực thi sau khi interrupt() đã nhận resume value.
    log.info("[node_human_review] Resumed — raw decision: %s", decision)

    if not isinstance(decision, dict):
        log.error(
            "[node_human_review] Invalid resume payload type=%s, defaulting to rejected",
            type(decision).__name__,
        )
        decision = {"action": "rejected", "feedback": "Invalid resume data format"}

    action: str = (decision.get("action") or "").strip().lower()
    feedback: str = (decision.get("feedback") or "").strip()

    # Chỉ cho phép 2 giá trị hợp lệ — fallback về rejected để tránh graph bị kẹt
    if action not in ("approved", "rejected"):
        log.warning(
            "[node_human_review] Unknown action=%r, defaulting to rejected", action
        )
        action = "rejected"

    log.info("[node_human_review] Decision processed — action=%s", action)

    # ─── 4. Emit frame ────────────────────────────────────────────────────────
    return StandardFrame.emit(
        registry_key=BusRegistry.HR,
        payload=BodyFrame(
            status="SUCCESS",
            text=draft,
            route=action,
            state={"process_completed": action == "approved"},
            context={"feedback": feedback},
        ),
    )