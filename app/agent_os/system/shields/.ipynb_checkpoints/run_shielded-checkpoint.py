# =============================================================================
# SHIELDED NODE EXECUTOR (PRE / POST GUARD WRAPPER)
# =============================================================================

from typing import Callable, Any, Dict, Awaitable
from functools import wraps

from agent_os.system.shields.shield_runtime import ShieldRuntime
from agent_os.system.shields.shield_faults import ShieldFault
from agent_os.system.shields.shield_telemetry import ShieldTelemetry
from agent_os.system.core_protocol import PipelineError


# =============================================================================
# GLOBAL SHIELD ENGINE (SINGLETON STYLE)
# =============================================================================

_SHIELD = ShieldRuntime()


# =============================================================================
# RUN SHIELDED WRAPPER
# =============================================================================

def shielded(
    node_name: str,
    fn: Callable[..., Awaitable[Dict[str, Any]]],
) -> Callable:
    """
    Wrap a LangGraph node with:
        PRE-GUARD  → sanitize input / block injection
        NODE       → execute logic
        POST-GUARD → validate output / enforce policy
    """

    @wraps(fn)
    async def wrapper(state, config):

        # =========================================================
        # 1. PRE-GUARD (INPUT SAFETY)
        # =========================================================
        try:
            safe_state = _SHIELD.pre_guard(
                node=node_name,
                state=state,
                config=config,
            )
        except ShieldFault as e:
            return {
                "errors": [
                    PipelineError(
                        node=node_name,
                        code="PRE_GUARD_BLOCK",
                        message=str(e),
                        recoverable=False,
                    )
                ],
                "aborted": True,
            }

        # =========================================================
        # 2. NODE EXECUTION
        # =========================================================
        try:
            raw_output = await fn(safe_state, config)

        except Exception as e:
            return {
                "errors": [
                    PipelineError(
                        node=node_name,
                        code=type(e).__name__,
                        message=str(e)[:300],
                        recoverable=True,
                    )
                ],
                "aborted": True,
            }

        # =========================================================
        # 3. POST-GUARD (OUTPUT SAFETY + POLICY)
        # =========================================================
        try:
            final_output = _SHIELD.post_guard(
                node=node_name,
                output=raw_output,
                state=safe_state,
                config=config,
            )

        except ShieldFault as e:
            return {
                "errors": [
                    PipelineError(
                        node=node_name,
                        code="POST_GUARD_BLOCK",
                        message=str(e),
                        recoverable=False,
                    )
                ],
                "aborted": True,
                "blog_stage_degraded": True,
            }

        # =========================================================
        # 4. TELEMETRY
        # =========================================================
        telemetry = ShieldTelemetry(
            node=node_name,
            status="ok",
        )

        if isinstance(final_output, dict):
            final_output["shield_telemetry"] = telemetry

        return final_output

    return wrapper