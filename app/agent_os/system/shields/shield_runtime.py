# =============================================================================
# SHIELD RUNTIME (CORE SECURITY ENGINE)
# =============================================================================

from dataclasses import dataclass
from typing import Any, Dict


# =============================================================================
# EXCEPTION
# =============================================================================

class ShieldFault(Exception):
    pass


# =============================================================================
# SHIELD ENGINE
# =============================================================================

class ShieldRuntime:

    # =========================
    # PRE-GUARD
    # =========================
    def pre_guard(self, node: str, state: Any, config: dict):

        text = getattr(state, "user_input", "")

        clean = self.sanitize(text)

        if self.detect_injection(clean):
            raise ShieldFault(f"[PRE_GUARD] injection detected in {node}")

        if len(clean) > 8000:
            raise ShieldFault(f"[PRE_GUARD] input too long in {node}")

        # inject sanitized back into state (immutable style)
        if hasattr(state, "model_copy"):
            state = state.model_copy(update={"user_input": clean})

        return state


    # =========================
    # POST-GUARD
    # =========================
    def post_guard(self, node: str, output: Any, state: Any, config: dict):

        if output is None:
            raise ShieldFault(f"[POST_GUARD] null output from {node}")

        if isinstance(output, dict):

            # schema check basic
            if "error" in output:
                raise ShieldFault(f"[POST_GUARD] error payload in {node}")

        # content policy
        if self.policy_violation(str(output)):
            raise ShieldFault(f"[POST_GUARD] policy violation in {node}")

        return output


    # =========================
    # SECURITY CORE
    # =========================

    def sanitize(self, text: str) -> str:
        return text.strip()

    def detect_injection(self, text: str) -> bool:
        signals = [
            "ignore previous",
            "system prompt",
            "jailbreak",
            "reveal secrets",
        ]
        t = text.lower()
        return any(s in t for s in signals)

    def policy_violation(self, text: str) -> bool:
        forbidden = [
            "guaranteed profit",
            "fake result",
            "illegal",
        ]
        t = text.lower()
        return any(f in t for f in forbidden)