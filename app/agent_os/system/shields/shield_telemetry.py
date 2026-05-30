import time

from pydantic import BaseModel, Field


class ShieldTelemetry(BaseModel):
    shield_name: str

    model: str

    session_id: str

    runtime_ms: float

    prompt_tokens: int = 0

    completion_tokens: int = 0

    total_tokens: int = 0

    cost_usd: float = 0.0

    success: bool = True

    error: str = ""

    ts: float = Field(default_factory=time.time)

    @classmethod
    def failure(
        cls,
        shield_name: str,
        model: str,
        session_id: str,
        error: str,
        runtime_ms: float = 0.0,
    ):
        return cls(
            shield_name=shield_name,
            model=model,
            session_id=session_id,
            runtime_ms=runtime_ms,
            success=False,
            error=error,
        )
