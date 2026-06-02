from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


class AnswerSource(str, Enum):
    CACHE  = "cache"
    RAG    = "rag"
    LLM    = "llm"
    SEARCH = "search"


class FinishReason(str, Enum):
    SUCCESS  = "success"
    FALLBACK = "fallback"
    ERROR    = "error"


class FinalResponseOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    answer:        str
    answer_source: AnswerSource
    finish_reason: FinishReason
    confidence:    float     = 1.0
    latency_ms:    float     = 0.0
    node_path:     list[str] = Field(default_factory=list)
    model:         str       = ""
    input_tokens:  int       = 0
    output_tokens: int       = 0