from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Any, Dict, List, Optional, Literal


# =========================================================
# COMPONENT REGISTRY — source of truth cho AI selector
# =========================================================

COMPONENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "ads_card": {
        "description": "Hiển thị nội dung quảng cáo: headline, body copy, CTA button, platform badge",
        "intent_tags": ["ads_only", "full_campaign"],
        "required_props": ["headline", "body"],
        "optional_props": ["cta_text", "platform", "tone"],
        "template_path": "widgets/ads_card.html",
    },
    "email_template": {
        "description": "Hiển thị email marketing: subject line, preheader, body HTML, CTA",
        "intent_tags": ["email_only", "full_campaign"],
        "required_props": ["subject", "body"],
        "optional_props": ["preheader", "cta_text", "cta_url"],
        "template_path": "widgets/email_template.html",
    },
    "blog_preview": {
        "description": "Hiển thị bài viết blog: title, excerpt, tags, estimated read time",
        "intent_tags": ["full_campaign"],
        "required_props": ["title", "content"],
        "optional_props": [
            "tags",
            "read_time_minutes",
            "seo_title",
            "meta_description",
        ],
        "template_path": "widgets/blog_preview.html",
    },
    "campaign_summary": {
        "description": "Hiển thị tổng quan chiến dịch khi có đủ ads + email + blog cùng lúc",
        "intent_tags": ["full_campaign"],
        "required_props": ["status", "components_ready"],
        "optional_props": ["message", "total_words"],
        "template_path": "widgets/campaign_summary.html",
    },
    "error_card": {
        "description": "Hiển thị lỗi hoặc cảnh báo khi một phần hoặc toàn bộ pipeline thất bại",
        "intent_tags": ["error", "fallback"],
        "required_props": ["message"],
        "optional_props": ["title", "error_code", "failed_node", "debug_details"],
        "template_path": "widgets/error_display.html",
    },
    "empty_state": {
        "description": "Hiển thị trạng thái rỗng (Zen style) khi pipeline chạy xong nhưng không có dữ liệu",
        "intent_tags": ["empty", "fallback"],
        "required_props": ["title"],
        "optional_props": ["description", "user_input"],
        "template_path": "widgets/empty_state.html",
    },
    "text_response": {
        "description": "Fallback: hiển thị plain text khi không có component phù hợp",
        "intent_tags": ["fallback", "invalid"],
        "required_props": ["text"],
        "optional_props": ["title"],
        "template_path": "widgets/text_response.html",
    },
}


# =========================================================
# PROPS SCHEMAS — validate từng component
# =========================================================


class AdsCardProps(BaseModel):
    headline: str = Field(..., max_length=200)
    body: str = Field(..., max_length=2000)
    cta_text: str = Field(default="Tìm hiểu thêm", max_length=50)
    platform: str = Field(default="general")
    tone: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class EmailTemplateProps(BaseModel):
    subject: str = Field(..., max_length=200)
    body: str = Field(..., max_length=10000)
    preheader: Optional[str] = Field(None, max_length=200)
    cta_text: Optional[str] = Field(None, max_length=50)
    cta_url: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class BlogPreviewProps(BaseModel):
    title: str = Field(..., max_length=300)
    content: str = Field(..., max_length=50000)
    tags: List[str] = Field(default_factory=list)
    read_time_minutes: Optional[int] = None
    seo_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=160)

    model_config = ConfigDict(extra="ignore")


class CampaignSummaryProps(BaseModel):
    status: str = Field(default="completed")
    components_ready: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    total_words: Optional[int] = None

    model_config = ConfigDict(extra="ignore")


# 🔥 ĐỒNG BỘ: Sửa lại Props của ErrorCard để map trùng khớp với file error_display.html của bạn
class ErrorCardProps(BaseModel):
    message: str = Field(
        ..., description="Nội dung thông báo lỗi thuần Việt hiển thị cho user"
    )
    title: Optional[str] = Field(default="Hệ thống thông báo")
    error_code: Optional[str] = Field(default="INTERNAL_ERROR")
    failed_node: Optional[str] = Field(default="System")
    debug_details: Optional[str] = Field(
        default=None, description="Chi tiết lỗi kỹ thuật (traceback)"
    )

    model_config = ConfigDict(extra="ignore")


# 🔥 BỔ SUNG: Thêm Props cho Empty State để validate các trường của file empty_state.html
class EmptyStateProps(BaseModel):
    title: str = Field(default="Không tìm thấy nội dung kết quả")
    description: Optional[str] = Field(None, max_length=1000)
    user_input: Optional[str] = Field(
        None, description="Câu prompt gốc của người dùng để hiển thị ngữ cảnh"
    )

    model_config = ConfigDict(extra="ignore")


class TextResponseProps(BaseModel):
    text: str
    title: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


# Map component_id → Pydantic model
PROPS_SCHEMA_MAP: Dict[str, type[BaseModel]] = {
    "ads_card": AdsCardProps,
    "email_template": EmailTemplateProps,
    "blog_preview": BlogPreviewProps,
    "campaign_summary": CampaignSummaryProps,
    "error_card": ErrorCardProps,
    "empty_state": EmptyStateProps,  # Đưa empty_state vào map schema
    "text_response": TextResponseProps,
}

# Thêm "empty_state" vào Literal định danh kiểu
ComponentId = Literal[
    "ads_card",
    "email_template",
    "blog_preview",
    "campaign_summary",
    "error_card",
    "empty_state",
    "text_response",
]


# =========================================================
# LLM RESPONSE SCHEMA — dùng lại cho rule-based selector
# =========================================================


class ComponentSelection(BaseModel):
    component_id: ComponentId
    props: Dict[str, Any]
    reason: Optional[str] = None  # debug only, không render

    model_config = ConfigDict(extra="ignore")


class LLMSelectorResponse(BaseModel):
    selections: List[ComponentSelection] = Field(..., min_length=1)

    @field_validator("selections")
    @classmethod
    def validate_component_ids(
        cls, v: List[ComponentSelection]
    ) -> List[ComponentSelection]:
        valid_ids = set(COMPONENT_REGISTRY.keys())
        for sel in v:
            if sel.component_id not in valid_ids:
                raise ValueError(f"Unknown component_id: {sel.component_id}")
        return v

    model_config = ConfigDict(extra="ignore")


# =========================================================
# NODE OUTPUT SCHEMA — emit vào MainBus
# =========================================================


class RenderedComponent(BaseModel):
    component_id: ComponentId
    props: Dict[str, Any]  # props đã validated
    template_path: str  # path cho Django/Jinja2 render_to_string

    model_config = ConfigDict(extra="ignore")


class UISelectorOutput(BaseModel):
    rendered_components: List[RenderedComponent] = Field(default_factory=list)
    fallback_used: bool = Field(default=False)
    selector_status: str = Field(default="success")  # "success" | "fallback" | "error"
    raw_text_fallback: Optional[str] = None  # populated khi fallback_used=True

    model_config = ConfigDict(frozen=True, extra="ignore")
