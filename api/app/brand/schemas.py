from pydantic import BaseModel, Field
from typing import List, Optional

class BrandVoiceRules(BaseModel):
    forbidden_words: List[str] = Field(default_factory=list, max_length=20)
    tone_patterns: List[str] = Field(default_factory=list, max_length=5)
    cta_patterns: List[str] = Field(default_factory=list, max_length=5)

class MessageObjection(BaseModel):
    objection: str
    counter: str

class Messaging(BaseModel):
    pain_points: List[str] = Field(default_factory=list, max_length=5)
    objections: List[MessageObjection] = Field(default_factory=list, max_length=5)
    proof_points: List[str] = Field(default_factory=list, max_length=10)

class ContentExamples(BaseModel):
    blog_post: Optional[str] = None
    social_post: Optional[str] = None
    ad_copy: Optional[str] = None
    landing_page: Optional[str] = None

class VisualIdentity(BaseModel):
    style_description: str
    color_palette: List[str] = Field(default_factory=list, max_length=5)
    mood: str

class BrandProfileSchema(BaseModel):
    """Full profile - 6 fields exactly matching DB relations"""
    positioning: str
    audience: str
    brand_voice_rules: BrandVoiceRules
    messaging: Messaging
    content_examples: ContentExamples
    visual_identity: VisualIdentity

    class Config:
        from_attributes = True

# Scoped profiles for agent prompts optimization
class WriterScope(BaseModel):
    positioning: str
    audience: str
    brand_voice_rules: BrandVoiceRules
    messaging: Messaging
    content_examples: ContentExamples

class DesignerScope(BaseModel):
    positioning: str
    visual_identity: VisualIdentity

class AdsScope(BaseModel):
    positioning: str
    audience: str
    brand_voice_rules: BrandVoiceRules
    messaging: Messaging
    content_examples: ContentExamples

class LandingPageScope(BaseModel):
    positioning: str
    audience: str
    brand_voice_rules: BrandVoiceRules
    messaging: Messaging
    content_examples: ContentExamples
    visual_identity: VisualIdentity