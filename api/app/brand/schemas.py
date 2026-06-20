from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
import re


# ═══════════════════════════════════════════════════════════════════
# SUB-SCHEMAS — 8 fields
# ═══════════════════════════════════════════════════════════════════

class ToneOverride(BaseModel):
    base: List[str] = Field(default_factory=list)
    overrides: Dict[str, List[str]] = Field(default_factory=dict)


class StyleConfig(BaseModel):
    sentenceLength: Literal["short", "medium", "long", "mixed"]
    voice: Literal["active", "passive"]
    perspective: Literal["first", "second", "third"]
    pronouns: Optional[Dict[str, str]] = Field(
        default_factory=lambda: {"ai": "Chúng tôi", "reader": "Quý khách"}
    )
    logo_url: Optional[str] = None


class VocabularyRules(BaseModel):
    wordsToUse: List[str] = Field(default_factory=list)
    wordsToAvoid: List[str] = Field(default_factory=list)
    phrasesToUse: List[str] = Field(default_factory=list)
    phrasesToAvoid: List[str] = Field(default_factory=list)
    topicsToAvoid: Optional[List[str]] = Field(default_factory=list)


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
    contentType: Literal["blog_web", "email_sale", "social_media", "ad","landing_page", "other"] 


class BrandEightFields(BaseModel):
    personality: str = Field(..., min_length=1)
    tone: ToneOverride
    style: StyleConfig
    vocabulary: VocabularyRules
    format_rules: FormatRules
    cta_style: CtaStyle
    examples: List[VoiceExample] = Field(default_factory=list)
    tone_funny_serious: int = Field(default=50, ge=0, le=100)
    tone_formal_casual: int = Field(default=50, ge=0, le=100)
    tone_respectful_irreverent: int = Field(default=50, ge=0, le=100)
    tone_enthusiastic_matter_of_fact: int = Field(default=50, ge=0, le=100)


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
        return list(dict.fromkeys(v))


# ═══════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class BrandCreate(BaseModel):
    """
    POST /brand-voices — tạo mới, LLM sẽ extract 8 fields từ research.
    
    Case 1: business_id đã có → skip research, dùng thẳng
    Case 2: business_id = None → tạo business mới + run pipeline research + extract voice
    """
    # Case 1: Existing business
    business_id: Optional[str] = Field(None, min_length=1)
    
    # Case 2: Create new business + research
    business_name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, max_length=500)
    industry: Optional[str] = Field(None, max_length=100)
    owner_id: Optional[str] = Field(None, min_length=1)
    website_url: str = Field(..., min_length=1, max_length=500)
    
    # Common
    voice_config: VoiceConfigIn

    tone_funny_serious: int = Field(default=50, ge=0, le=100)
    tone_formal_casual: int = Field(default=50, ge=0, le=100)
    tone_respectful_irreverent: int = Field(default=50, ge=0, le=100)
    tone_enthusiastic_matter_of_fact: int = Field(default=50, ge=0, le=100)
    
    @field_validator("website_url")
    @classmethod
    def validate_fb_url(cls, v: str) -> str:
        pattern = r'^https?://(www\.)?(facebook|fb)\.com/[a-zA-Z0-9.]{5,}$'
        if not re.match(pattern, v):
            raise ValueError("website_url must be a valid Facebook URL (https://www.facebook.com/...)")
        return v.rstrip("/")
    
    @model_validator(mode="after")
    def validate_business_input(self) -> BrandCreate:
        """Ensure either business_id OR (business_name + owner_id) is provided."""
        has_business_id = bool(self.business_id and self.business_id.strip())
        has_new_business = bool(self.business_name and self.business_name.strip())
        
        if not has_business_id and not has_new_business:
            raise ValueError(
                "Phải cung cấp business_id hoặc business_name + owner_id"
            )
        
        if has_business_id and has_new_business:
            raise ValueError(
                "Không thể cung cấp cả business_id và business_name cùng lúc"
            )
        
        # Nếu tạo mới, owner_id bắt buộc
        if has_new_business and not self.owner_id:
            raise ValueError("owner_id bắt buộc khi tạo business mới")
        
        return self


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

    tone_funny_serious: Optional[int] = Field(None, ge=0, le=100)
    tone_formal_casual: Optional[int] = Field(None, ge=0, le=100)
    tone_respectful_irreverent: Optional[int] = Field(None, ge=0, le=100)
    tone_enthusiastic_matter_of_fact: Optional[int] = Field(None, ge=0, le=100)

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

    tone_funny_serious: int
    tone_formal_casual: int
    tone_respectful_irreverent: int
    tone_enthusiastic_matter_of_fact: int

    is_default: str
    created_at: datetime
    updated_at: datetime

    metadata_info: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"from_attributes": True}


class BrandListOut(BaseModel):
    items: List[BrandOut]
    total: int