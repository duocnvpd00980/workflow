# output_guard_service.py
import re
from .output_guard_protocol import OutputGuardResult

_PII_PATTERNS = [
    r"\b\d{9,12}\b",                          # CCCD / số điện thoại
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # email
    r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",           # số thẻ
]

_TOXIC_KEYWORDS = [
    "chết đi", "tự tử", "giết", "thù hận",
]

_MIN_LENGTH = 10
_MAX_LENGTH = 8000


class OutputGuardService:

    def check(self, text: str) -> OutputGuardResult:

        # 1. Empty
        if not text or not text.strip():
            return OutputGuardResult(
                is_safe=False,
                violation="empty",
                reason="Response rỗng.",
            )

        # 2. Too short
        if len(text.strip()) < _MIN_LENGTH:
            return OutputGuardResult(
                is_safe=False,
                violation="too_short",
                reason=f"Response quá ngắn: {len(text)} ký tự.",
            )

        # 3. Too long
        if len(text) > _MAX_LENGTH:
            return OutputGuardResult(
                is_safe=False,
                violation="too_long",
                reason=f"Response quá dài: {len(text)} ký tự.",
            )

        # 4. PII
        for pattern in _PII_PATTERNS:
            if re.search(pattern, text):
                return OutputGuardResult(
                    is_safe=False,
                    violation="pii",
                    reason="Phát hiện thông tin nhạy cảm (PII).",
                )

        # 5. Toxic
        text_lower = text.lower()
        for keyword in _TOXIC_KEYWORDS:
            if keyword in text_lower:
                return OutputGuardResult(
                    is_safe=False,
                    violation="toxic",
                    reason=f"Phát hiện nội dung độc hại: '{keyword}'.",
                )

        return OutputGuardResult(is_safe=True, violation="none")