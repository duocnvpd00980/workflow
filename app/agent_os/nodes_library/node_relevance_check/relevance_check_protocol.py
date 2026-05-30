from pydantic import BaseModel, ConfigDict
from typing import Literal


class RelevanceCheckOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    relevance_status: Literal["high_rel", "low_rel"]
    top_score: float | None
    reason: str
