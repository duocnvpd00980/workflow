from pydantic import BaseModel, Field
from typing import Literal


class SeedOutput(BaseModel):
    raw_input: str
    normalized_input: str
    intent: Literal["ads", "email", "blog", "unknown"]
    language: str = "vi"
    brand_color: str = "#000000"
    confidence: float = 0.0
