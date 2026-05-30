from pydantic import BaseModel, ConfigDict
from typing import Any

class KnowledgebaseOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    retrieved_context: str
    source_nodes: list[dict[str, Any]]
    top_score: float | None
    node_count: int