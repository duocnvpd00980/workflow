from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ── Create ───────────────────────────────────────────────────────────
class BrandCreate(BaseModel):
    business_id: Optional[str] = None
    owner_id: str
    business_name: str
    website_url: Optional[str] = None

# ── Read (GET) — trả nguyên K1-K7 dạng Markdown ────────────────────
class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    business_id: str
    metadata_info: Optional[Dict[str, Any]] = None
    name: str
    purpose: str
    target_audience: str
    desired_tone: str
    channels: List[str] = Field(default_factory=list)
    website_url: Optional[str] = None
    k1_brand_foundation: Optional[str] = None
    k2_customer_insights: Optional[str] = None
    k3_content_patterns: Optional[str] = None
    k4_behavior_rules: Optional[str] = None
    k5_examples: Optional[str] = None
    k6_tone_analysis: Optional[str] = None
    k7_vocabulary_rules: Optional[str] = None
    taglines: Optional[List[str]] = None
    business_facts: Optional[Dict[str, Any]] = None
    brand_summary: Optional[str] = None
    tone_funny_serious: int
    tone_formal_casual: int
    tone_respectful_irreverent: int
    tone_enthusiastic_matter_of_fact: int
    is_default: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


# ── List (GET /brand-voices) ───────────────────────────────────────
class BrandListOut(BaseModel):
    items: List[BrandOut]
    total: int


# ── Update (PATCH) — cho phép cập nhật trực tiếp từng block Markdown ──
class BrandUpdate(BaseModel):
    name: Optional[str] = None
    purpose: Optional[str] = None
    target_audience: Optional[str] = None
    desired_tone: Optional[str] = None
    channels: Optional[List[str]] = None
    website_url: Optional[str] = None
    k1_brand_foundation: Optional[str] = None
    k2_customer_insights: Optional[str] = None
    k3_content_patterns: Optional[str] = None
    k4_behavior_rules: Optional[str] = None
    k5_examples: Optional[str] = None
    k6_tone_analysis: Optional[str] = None
    k7_vocabulary_rules: Optional[str] = None
    taglines: Optional[List[str]] = None
    business_facts: Optional[Dict[str, Any]] = None
    tone_funny_serious: Optional[int] = None
    tone_formal_casual: Optional[int] = None
    tone_respectful_irreverent: Optional[int] = None
    tone_enthusiastic_matter_of_fact: Optional[int] = None
    is_default: Optional[str] = None