from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Helpers ─────────────────────────────────────────────────────

def _slugify(value: str) -> str:
    """'Mường Thanh Luxury' → 'muong-thanh-luxury'"""
    import unicodedata
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[\s_-]+", "-", value)


# ── Request ──────────────────────────────────────────────────────

class BusinessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    owner_id: str
    industry: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class BusinessUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


# ── Response ─────────────────────────────────────────────────────

class BusinessOut(BaseModel):
    id: str
    name: str
    slug: str
    owner_id: str
    industry: Optional[str]
    address: Optional[str]
    website: Optional[str]
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BusinessListOut(BaseModel):
    items: list[BusinessOut]
    total: int
