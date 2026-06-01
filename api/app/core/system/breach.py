# agent_os/system/breach.py
# ============================================================
# SYSTEM BREACH — như hardware interrupt, không thể bị bắt
# Kế thừa BaseException, KHÔNG phải Exception
# → xuyên qua mọi try/except trong LangGraph, node, shield
# ============================================================


class Breach(BaseException):
    """Trip không thể chặn. Chỉ finally chạy được."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"[SYSTEM BREACH] {reason}")
