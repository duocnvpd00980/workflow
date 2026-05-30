from pydantic import BaseModel, ConfigDict
from typing import Literal


class CacheLayerOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    cache_status: Literal["hit", "miss"]
    cached_answer: str | None
    cache_tier: Literal["L1", "L2", "none"]
    similarity_score: float | None
