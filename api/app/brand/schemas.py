from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


# ═══════════════════════════════════════════════════════════════════
# SUB-SCHEMAS — 8 fields
# ═══════════════════════════════════════════════════════════════════

class ToneOverride(BaseModel):
    base: List[str] = Field(default_factory=list)  # ← Bỏ min_length=1
    overrides: Dict[str, List[str]] = Field(default_factory=dict)
    # e.g. {"blog": ["formal"], "social": ["playful"]}


class StyleConfig(BaseModel):
    sentenceLength: Literal["short", "medium", "long", "mixed"]
    voice: Literal["active", "passive"]
    perspective: Literal["first", "second", "third"]


class VocabularyRules(BaseModel):
    wordsToUse: List[str] = Field(default_factory=list)
    wordsToAvoid: List[str] = Field(default_factory=list)
    phrasesToUse: List[str] = Field(default_factory=list)
    phrasesToAvoid: List[str] = Field(default_factory=list)


class FormatRules(BaseModel):
    paragraphMaxSentences: int = Field(..., ge=1, le=20)
    useEmoji: bool
    useHashtags: bool
    bulletPointStyle: Literal["dash", "dot", "number", "arrow", "none"]


class CtaStyle(BaseModel):
    style: Literal["soft", "direct", "urgent", "none"]
    phrases: List[str] = Field(default_factory=list)


class VoiceExample(BaseModel):
    input: str = Field(..., min_length=1)
    output: str = Field(..., min_length=1)
    contentType: Literal["blog", "email", "social", "ad", "other"]


class BrandEightFields(BaseModel):
    personality: str = Field(..., min_length=1)
    tone: ToneOverride
    style: StyleConfig
    vocabulary: VocabularyRules
    format_rules: FormatRules
    cta_style: CtaStyle
    examples: List[VoiceExample] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# VOICE CONFIG — user nhập
# ═══════════════════════════════════════════════════════════════════

VALID_CHANNELS = {"social", "blog", "email", "ad", "landing_page", "push", "sms"}

class VoiceConfigIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    purpose: str = Field(..., min_length=1, max_length=500)
    channels: List[str] = Field(default_factory=list)
    desired_tone: str = Field(..., min_length=1, max_length=100)
    target_audience: str = Field(..., min_length=1, max_length=500)

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: List[str]) -> List[str]:
        invalid = set(v) - VALID_CHANNELS
        if invalid:
            raise ValueError(
                f"Invalid channel(s): {invalid}. "
                f"Allowed: {VALID_CHANNELS}"
            )
        return list(dict.fromkeys(v))  # deduplicate, preserve order


# ═══════════════════════════════════════════════════════════════════
# RAG SOURCE
# ═══════════════════════════════════════════════════════════════════

class RagSource(BaseModel):
    website_url: Optional[str] = None
    uploaded_files: List[str] = Field(default_factory=list)
    pasted_text: Optional[str] = None

    # @model_validator(mode="after")
    # def at_least_one_source(self) -> RagSource:
    #     has_url = bool(self.website_url)
    #     has_files = bool(self.uploaded_files)
    #     has_text = bool(self.pasted_text and self.pasted_text.strip())
    #     if not (has_url or has_files or has_text):
    #         raise ValueError(
    #             "Cần ít nhất một RAG source: website_url, uploaded_files, hoặc pasted_text."
    #         )
    #     return self


# ═══════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class BrandCreate(BaseModel):
    """POST /brand-voices — tạo mới, LLM sẽ extract 8 fields từ rag_source."""
    business_id: str = Field(..., min_length=1)
    voice_config: VoiceConfigIn
    rag_source: Optional[RagSource] = None


class BrandUpdate(BaseModel):
    """PATCH /brand-voices/{id} — cập nhật một phần (tất cả optional)."""
    # Voice config
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    purpose: Optional[str] = Field(None, min_length=1, max_length=500)
    channels: Optional[List[str]] = None
    desired_tone: Optional[str] = Field(None, min_length=1, max_length=100)
    target_audience: Optional[str] = Field(None, min_length=1, max_length=500)

    # 8 fields (user override sau khi LLM extract)
    personality: Optional[str] = None
    tone: Optional[ToneOverride] = None
    style: Optional[StyleConfig] = None
    vocabulary: Optional[VocabularyRules] = None
    format_rules: Optional[FormatRules] = None
    cta_style: Optional[CtaStyle] = None
    examples: Optional[List[VoiceExample]] = None

    is_default: Optional[Literal["0", "1"]] = None

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        invalid = set(v) - VALID_CHANNELS
        if invalid:
            raise ValueError(f"Invalid channel(s): {invalid}.")
        return list(dict.fromkeys(v))


# ═══════════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class BrandOut(BaseModel):
    id: str
    business_id: str

    # Voice config
    name: str
    purpose: str
    channels: List[str]
    desired_tone: str
    target_audience: str

    # 8 fields — Optional vì LLM có thể chưa extract xong
    personality: Optional[str] = None
    tone: Optional[ToneOverride] = None
    style: Optional[StyleConfig] = None
    vocabulary: Optional[VocabularyRules] = None
    format_rules: Optional[FormatRules] = None
    cta_style: Optional[CtaStyle] = None
    examples: List[VoiceExample] = Field(default_factory=list)

    # RAG source (trả về để user biết nguồn đã dùng)
    website_url: Optional[str] = None
    uploaded_files: List[str] = Field(default_factory=list)

    is_default: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BrandListOut(BaseModel):
    items: List[BrandOut]
    total: int