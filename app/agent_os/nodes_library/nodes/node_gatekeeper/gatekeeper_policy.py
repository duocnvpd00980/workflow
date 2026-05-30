"""
gatekeeper_policy.py — Production SaaS v3
==========================================
Tách policy config ra khỏi service logic.
Ops team có thể hot-reload hoặc load từ DB/S3 mà không cần redeploy.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GatekeeperPolicy:
    """
    Immutable policy snapshot.
    Tạo instance mới khi cần thay đổi (immutable = thread-safe).
    """

    # ── Forbidden lists ───────────────────────────────────────────────
    competitor_names: tuple[str, ...] = (
        "ChatGPT",
        "OpenAI",
        "Gemini",
        "Copilot",
        "Grok",
        "Mistral",
        "Llama",
        "Perplexity",
        # "Claude" — intentionally excluded: product name conflict
    )

    injection_signals: tuple[str, ...] = (
        # English
        "ignore previous",
        "disregard previous",
        "forget previous",
        "system prompt",
        "act as",
        "jailbreak",
        "bypass",
        "override instructions",
        "new persona",
        "pretend you are",
        "you are now",
        "developer mode",
        "dan mode",
        # Vietnamese
        "bỏ qua lệnh trước",
        "quên hướng dẫn",
        "giả vờ là",
        "vượt qua hệ thống",
    )

    vn_profanity: tuple[str, ...] = (
        # Explicit
        "cc",
        "cặc",
        "lồn",
        "đm",
        "đmm",
        "đcm",
        "vãi lồn",
        "dmm",
        "clgt",
        "đéo",
        "địt",
        "đụ",
        # Obfuscated
        "l**",
        "c**",
        "đ**",
        "c.c",
    )

    brand_replacement: str = "Holo AI"

    # ── Risk weights ──────────────────────────────────────────────────
    w_profanity: float = 0.35
    w_competitor: float = 0.60  # standalone competitor mention → block
    w_injection: float = 1.00  # always hard-block
    w_spam: float = 0.25

    # ── Thresholds ────────────────────────────────────────────────────
    block_threshold: float = 0.50  # risk_score >= threshold → blocked
    spam_unique_ratio: float = 0.40  # < ratio → spam
    spam_min_words: int = 5  # minimum tokens to trigger spam check
    max_input_chars: int = 10_000  # hard truncate before any processing

    # ── Audit ─────────────────────────────────────────────────────────
    enable_audit_log: bool = True
    redact_pii: bool = True  # sha256 input instead of storing raw


# ── Singleton default — override via dependency injection ──────────────────
DEFAULT_POLICY = GatekeeperPolicy()
