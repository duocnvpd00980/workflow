from pydantic import BaseModel


class ContentItem(BaseModel):

    content: str = ""

    agent: str = ""

    language_detected: str = ""

    has_cta: bool = False