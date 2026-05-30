from langchain_protocol import Any
from pydantic import BaseModel, Field
from typing import List


class BlogSection(BaseModel):
    heading: str = Field(..., description="Tiêu đề đoạn văn")
    main_point: str = Field(..., description="Ý chính cần truyền tải")
    keywords: List[str] = Field(default_factory=list)


class BlogPlan(BaseModel):
    title_suggestion: str = Field(..., min_length=5)
    outline: List[BlogSection] = Field(..., min_items=2)
    tone_of_voice: str = Field(default="Professional")

    model_config = {"frozen": True, "extra": "ignore"}


class PlannerParser:
    @staticmethod
    def parse(raw: Any) -> BlogPlan:
        try:
            return BlogPlan.model_validate(raw)
        except Exception:
            return BlogPlan(
                title_suggestion="[DRAFT] Kế hoạch nội dung mới",
                outline=[BlogSection(heading="Mở đầu", main_point="Giới thiệu chủ đề")],
                tone_of_voice="Neutral",
            )
