from pydantic import BaseModel


class NodeAudit(BaseModel):
    node: str
    model: str
    session_id: str
    runtime_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    success: bool