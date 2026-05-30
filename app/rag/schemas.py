from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from pydantic import BaseModel


# ── Internal pipeline types ───────────────────────────────
@dataclass
class Doc:
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Chunk:
    score: float
    text: str
    meta: dict


@dataclass
class Result:
    query: str
    chunks: list[Chunk]
    source: str


# ── API response schemas ──────────────────────────────────
class DocOut(BaseModel):
    id: int
    title: str
    status: str
    chunk_count: int
    file_size: Optional[str] = None
    created_at: str


class UploadOut(BaseModel):
    id: int
    title: str
    status: str
    message: str


class SearchOut(BaseModel):
    query: str
    results: list[dict]
    source: str