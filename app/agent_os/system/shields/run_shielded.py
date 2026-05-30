# =============================================================================
# SHIELDED NODE EXECUTOR (PRODUCTION GRADE)
# =============================================================================

from __future__ import annotations

import asyncio
import logging
import time

from functools import wraps

from typing import (
    Any,
    Awaitable,
    Callable,
)

from langchain_core.runnables import (
    RunnableConfig,
)

from agent_os.system.bus.protocol import (
    StandardFrame,
    Telemetry,
)

from agent_os.system.shields.shield_faults import (
    PipelineError,
    ShieldFault,
)

from agent_os.system.shields.shield_runtime import (
    ShieldRuntime,
)

# =============================================================================
# LOGGER
# =============================================================================

logger = logging.getLogger("agent_os.runtime")

# =============================================================================
# SHIELD RUNTIME
# =============================================================================

_SHIELD = ShieldRuntime()

# =============================================================================
# CONFIG
# =============================================================================

NODE_TIMEOUT_SECONDS = 60

# =============================================================================
# TOKEN PRICING TABLE
# =============================================================================

MODEL_PRICING = {
    "default": {
        "input_per_1k": 0.0005,
        "output_per_1k": 0.0015,
    }
}

# =============================================================================
# COST CALCULATOR
# =============================================================================


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model_name: str = "default",
) -> float:

    pricing = MODEL_PRICING.get(
        model_name,
        MODEL_PRICING["default"],
    )

    input_cost = (input_tokens / 1000) * pricing["input_per_1k"]

    output_cost = (output_tokens / 1000) * pricing["output_per_1k"]

    return round(
        input_cost + output_cost,
        8,
    )


# =============================================================================
# SAFE TOKEN EXTRACTION
# =============================================================================


def extract_usage_metrics(
    usage: Any,
) -> tuple[int, int, int]:

    if usage is None:
        return (
            0,
            0,
            0,
        )

    return (
        getattr(
            usage,
            "prompt_tokens",
            0,
        ),
        getattr(
            usage,
            "completion_tokens",
            0,
        ),
        getattr(
            usage,
            "total_tokens",
            0,
        ),
    )


# =============================================================================
# SHIELDED EXECUTION WRAPPER
# =============================================================================


def shielded(
    node_name: str,
    fn: Callable[
        [Any, RunnableConfig | None],
        Awaitable[dict],
    ],
) -> Callable[
    [Any, RunnableConfig | None],
    Awaitable[dict],
]:

    @wraps(fn)
    async def wrapper(
        state: Any,
        config: RunnableConfig | None = None,
    ) -> dict:

        start_time = time.perf_counter()

        logger.info(
            "[%s] execution_started",
            node_name,
        )

        # =====================================================
        # PRE GUARD
        # =====================================================

        try:
            safe_state = _SHIELD.pre_guard(
                node=node_name,
                state=state,
                config=config,
            )

            if safe_state is None:
                safe_state = state

        except ShieldFault as e:
            logger.exception(
                "[%s] pre_guard_failed",
                node_name,
            )

            raise PipelineError(f"{node_name} PRE_GUARD_BLOCK: {str(e)}") from e

        # =====================================================
        # NODE EXECUTION
        # =====================================================

        try:
            final_output = await asyncio.wait_for(
                fn(
                    safe_state,
                    config,
                ),
                timeout=NODE_TIMEOUT_SECONDS,
            )

            if final_output is None:
                raise PipelineError(f"{node_name} returned None")

            if not isinstance(
                final_output,
                dict,
            ):
                raise PipelineError(f"{node_name} must return dict")

        except asyncio.TimeoutError as e:
            logger.exception(
                "[%s] timeout",
                node_name,
            )

            raise PipelineError(f"{node_name} TIMEOUT") from e

        except Exception as e:
            logger.exception(
                "[%s] execution_failed",
                node_name,
            )

            raise PipelineError(f"{node_name} EXECUTION_FAILED: {str(e)}") from e

        # =====================================================
        # POST GUARD
        # =====================================================

        try:
            guarded_output = _SHIELD.post_guard(
                node=node_name,
                output=final_output,
                state=safe_state,
                config=config,
            )

            if guarded_output is not None:
                final_output = guarded_output

        except ShieldFault as e:
            logger.exception(
                "[%s] post_guard_failed",
                node_name,
            )

            raise PipelineError(f"{node_name} POST_GUARD_BLOCK: {str(e)}") from e

        # =====================================================
        # EXECUTION TIME
        # =====================================================

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        # =====================================================
        # TELEMETRY ENRICHMENT
        # =====================================================

        updated_output: dict = {}

        for reg_key, frame in final_output.items():
            if not isinstance(
                frame,
                StandardFrame,
            ):
                updated_output[reg_key] = frame

                continue

            payload = frame.payload

            usage = None

            # =================================================
            # SAFE USAGE EXTRACTION
            # =================================================

            if hasattr(
                payload,
                "usage",
            ):
                usage = payload.usage

            elif isinstance(
                payload,
                dict,
            ):
                usage = payload.get("usage")

            (
                input_tokens,
                output_tokens,
                total_tokens,
            ) = extract_usage_metrics(usage)

            model_name = "default"

            if isinstance(
                payload,
                dict,
            ):
                model_name = payload.get(
                    "model",
                    "default",
                )

            estimated_cost = calculate_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_name=model_name,
            )

            telemetry = Telemetry(
                latency_ms=duration_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=estimated_cost,
            )

            updated_frame = frame.model_copy(update={"telemetry": telemetry})

            updated_output[reg_key] = updated_frame

            logger.info(
                "[%s] latency=%sms tokens=%s cost=$%s",
                node_name,
                duration_ms,
                total_tokens,
                estimated_cost,
            )

        logger.info(
            "[%s] execution_completed",
            node_name,
        )

        return updated_output

    return wrapper
