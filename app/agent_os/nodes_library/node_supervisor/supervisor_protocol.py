from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class SupervisorResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    next_agent: Literal["smalltalk", "knowledge", "marketing", "end"]
    instruction: str
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""
