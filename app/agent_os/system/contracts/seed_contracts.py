from pydantic import BaseModel


class SeedStrategy(BaseModel):

    target_audience: str = "general"

    main_benefit: str = "engagement"

    brand_voice: str = "professional"

    keyword: str = "marketing"

    language: str = "vi"

    tone: str = "professional"

    content_rules: str = ""