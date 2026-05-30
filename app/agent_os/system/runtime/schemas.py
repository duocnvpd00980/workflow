# agent_os/system/knowledge/schemas.py

from pydantic import BaseModel, Field

from typing import List, Dict, Any


# =========================================================
# INGEST RESULT
# =========================================================

class IngestResult(BaseModel):

    status: str = Field(
        default="success"
    )

    chunks_created: int = Field(
        default=0
    )

    source: str = Field(
        default="unknown"
    )


# =========================================================
# RETRIEVED CHUNK
# =========================================================

class RetrievedChunk(BaseModel):

    text: str

    score: float = Field(
        default=0.0
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )


# =========================================================
# SEARCH RESULT
# =========================================================

class RetrievalResult(BaseModel):

    query: str

    chunks: List[RetrievedChunk] = Field(
        default_factory=list
    )

    total_chunks: int = Field(
        default=0
    )