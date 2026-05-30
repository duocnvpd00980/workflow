"""
=======================================================================
CERTIFIED PROTOCOL WORKFLOW: node_input_guard
=======================================================================
BUSINESS INTENT
  Kiểm tra, làm sạch và chặn đứng các rủi ro bảo mật trước Supervisor.
=======================================================================
"""

from agent_os.nodes_library.node_input_guard.input_guard_protocol import (
    InputGuardOutput,
)
from agent_os.nodes_library.node_input_guard.input_guard_service import (
    InputGuardService,
)
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.protocol import BodyFrame, StandardFrame
from agent_os.system.bus.registry import BusRegistry


async def node_input_guard(state: MainBus):

    # =========================================================
    # S1 SAFE POST-GUARD
    # =========================================================
    if not hasattr(state, "user_input") or state.user_input is None:
        return StandardFrame.emit(
            registry_key=BusRegistry.IG,
            payload=BodyFrame(
                status="FAILED",
                text="Missing user_input on MainBus",
                error="MISSING_USER_INPUT",
                state={
                    "is_safe": False,
                    "sanitized_text": "",
                    "risk_category": "EMPTY_INPUT",
                    # ===== MOCK FOR SUPERVISOR =====
                    "history": [],
                    "user_profile": {},
                    "relevant_episodes": [],
                    "evaluation_feedback": "",
                },
            ),
        )

    raw_query: str = state.user_input

    # =========================================================
    # S2 CONTEXT (minimal)
    # =========================================================
    ctx = None

    # =========================================================
    # S3 DOMAIN EXECUTION
    # =========================================================
    service = InputGuardService()

    domain_result: InputGuardOutput = service.run(raw_query=raw_query)
    # =========================================================
    # S4 NORMALIZATION + EMIT
    # =========================================================
    if not domain_result.is_safe:
        return StandardFrame.emit(
            registry_key=BusRegistry.IG,
            payload=BodyFrame(
                status="FAILED",
                text=f"Blocked: {domain_result.risk_category}",
                error=f"SECURITY_{domain_result.risk_category}",
                state={
                    "is_safe": False,
                    "sanitized_text": domain_result.sanitized_text,
                    "risk_category": domain_result.risk_category,
                    "user_input": raw_query,
                    # ===== MOCK FOR SUPERVISOR =====
                    "history": [{"role": "user", "content": raw_query}],
                    "user_profile": {"user_id": "mock_user", "persona": "tester"},
                    "relevant_episodes": [],
                    "evaluation_feedback": "",
                },
            ),
        )

    return StandardFrame.emit(
        registry_key=BusRegistry.IG,
        payload=BodyFrame(
            status="SUCCESS",
            text=domain_result.sanitized_text,
            records=[],
            entities=[],
            state={
                "is_safe": True,
                "sanitized_text": domain_result.sanitized_text,
                "risk_category": domain_result.risk_category,
                "user_input": raw_query,
                # =================================================
                # MOCK DATA CHO SUPERVISOR (_safe_extract_* chạy)
                # =================================================
                "history": [
                    {"role": "user", "content": raw_query},
                    {"role": "assistant", "content": "acknowledged"},
                ],
                "user_profile": {
                    "user_id": "mock_user_001",
                    "persona": "marketing_user",
                },
                "relevant_episodes": [
                    {"event": "previous_query", "summary": "user asked about marketing"}
                ],
                "evaluation_feedback": "",
            },
            metrics={},
            context={},
            error=None,
        ),
    )
