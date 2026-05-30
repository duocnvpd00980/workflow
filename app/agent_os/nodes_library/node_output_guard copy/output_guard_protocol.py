# output_guard_protocol.py
from pydantic import BaseModel
from typing import Literal


class OutputGuardResult(BaseModel):
    is_safe: bool
    reason: str = ""
    violation: Literal[
        "none",
        "pii",
        "toxic",
        "too_short",
        "too_long",
        "empty",
    ] = "none"
