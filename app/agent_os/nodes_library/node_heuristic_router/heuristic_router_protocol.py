from pydantic import BaseModel, ConfigDict
from typing import Literal

class HeuristicRouterOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    route: Literal["smalltalk", "rag_knowledge", "general_chat"]
    matched_keyword: str | None
    query_snapshot: str