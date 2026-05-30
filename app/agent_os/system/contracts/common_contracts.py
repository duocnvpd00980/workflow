

import time
from pydantic import BaseModel, Field


class NodeAudit(BaseModel):
    """Per-node telemetry appended to the audit trail on the bus."""
    node:              str
    model:             str
    session_id:        str
    runtime_ms:        float
    prompt_tokens:     int   = 0
    completion_tokens: int   = 0
    total_tokens:      int   = 0
    cost_usd:          float = 0.0
    success:           bool  = True
    error:             str   = ""
    ts:                float = Field(default_factory=time.time)
 
    @classmethod
    def failure(
        cls,
        node: str,
        model: str,
        session_id: str,
        error: str,
        runtime_ms: float = 0.0,
    ) -> "NodeAudit":
        return cls(node=node, model=model, session_id=session_id,
                   runtime_ms=round(runtime_ms, 1), success=False, error=error)