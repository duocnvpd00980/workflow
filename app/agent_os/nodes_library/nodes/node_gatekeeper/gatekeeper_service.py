# agent_os/nodes_library/node_gatekeeper/gatekeeper_service.py

import logging
import time

from typing import NamedTuple
from enum import Enum

from .gatekeeper_protocol import GatekeeperOutput


# =============================================================================
# VIOLATION TYPES
# =============================================================================

class ViolationType(str, Enum):

    SPAM = "SPAM"

    INJECTION = "INJECTION"

    COMPETITOR = "COMPETITOR"

    PROFANITY = "PROFANITY"

    COLOR_ABUSE = "COLOR_ABUSE"


# =============================================================================
# DETECTOR HIT
# =============================================================================

class _DetectorHit(NamedTuple):

    violation: ViolationType

    triggered: bool

    weight: float

    detail: str | None = None


logger = logging.getLogger(__name__)


# =============================================================================
# GATEKEEPER SERVICE
# =============================================================================

class GatekeeperService:

    def __init__(self):

        # =========================================================
        # SECURITY CONFIG
        # =========================================================

        self.block_threshold = 0.5

        self.max_input_chars = 5000

        self.injection_signals = [
            "<script",
            "drop table",
            "delete from",
            "truncate table",
            "union select",
        ]

    # =========================================================================
    # INPUT GUARD
    # =========================================================================

    def _guard_input(
        self,
        text: str,
    ) -> str:

        text = (text or "").strip()

        return text[:self.max_input_chars]

    # =========================================================================
    # INJECTION DETECTOR
    # =========================================================================

    def _check_injection(
        self,
        text: str,
    ) -> _DetectorHit:

        text_low = text.lower()

        matched = next(
            (
                signal
                for signal in self.injection_signals
                if signal in text_low
            ),
            None,
        )

        return _DetectorHit(
            violation=ViolationType.INJECTION,
            triggered=matched is not None,
            weight=1.0,
            detail=matched,
        )

    # =========================================================================
    # SPAM DETECTOR
    # =========================================================================

    def _check_spam(
        self,
        text: str,
    ) -> _DetectorHit:

        words = text.lower().split()

        if len(words) < 5:

            return _DetectorHit(
                violation=ViolationType.SPAM,
                triggered=False,
                weight=0.0,
            )

        unique_ratio = len(set(words)) / len(words)

        return _DetectorHit(
            violation=ViolationType.SPAM,
            triggered=unique_ratio < 0.3,
            weight=0.4,
        )

    # =========================================================================
    # MAIN EXECUTION
    # =========================================================================

    async def run(
        self,
        seed: dict,
        *,
        tenant_id: str | None = None,
        thread_id: str | None = None,
    ) -> GatekeeperOutput:

        t_start = time.perf_counter()

        # =========================================================
        # NORMALIZE INPUT
        # =========================================================

        raw_head = self._guard_input(
            seed.get("headline", "")
        )

        raw_cont = self._guard_input(
            seed.get("content", "")
        )

        full_text = f"{raw_head} {raw_cont}"

        # =========================================================
        # DETECTORS
        # =========================================================

        hits = [

            self._check_injection(full_text),

            self._check_spam(full_text),
        ]

        # =========================================================
        # SCORE
        # =========================================================

        risk_score = sum(
            hit.weight
            for hit in hits
            if hit.triggered
        )

        violations = [
            hit.violation.value
            for hit in hits
            if hit.triggered
        ]

        # =========================================================
        # DECISION
        # =========================================================

        passed = risk_score < self.block_threshold

        # IMPORTANT:
        # STRING ONLY (checkpoint-safe)
        reason = (
            "OK"
            if passed
            else "POLICY_VIOLATION"
        )

        latency_ms = (
            time.perf_counter() - t_start
        ) * 1000

        # =========================================================
        # OBSERVABILITY LOG
        # =========================================================

        logger.info(
            (
                "Gatekeeper Check | "
                f"passed={passed} | "
                f"score={risk_score:.2f} | "
                f"latency={latency_ms:.2f}ms | "
                f"tenant_id={tenant_id} | "
                f"thread_id={thread_id}"
            )
        )

        # =========================================================
        # OUTPUT
        # =========================================================

        return GatekeeperOutput(

            gatekeeper_passed=passed,

            headline=raw_head if passed else "",

            content=raw_cont if passed else "",

            brand_color=seed.get(
                "brand_color",
                "#000000",
            ),

            risk_score=min(
                risk_score,
                1.0,
            ),

            violations=violations,

            # IMPORTANT:
            # PURE STRING
            reason=reason,

            reason_detail=(
                f"Risk too high: {risk_score}"
                if not passed
                else None
            ),
        )