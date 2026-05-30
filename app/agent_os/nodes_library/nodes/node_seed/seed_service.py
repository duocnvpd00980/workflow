import re
from langdetect import detect
from .seed_protocol import SeedOutput


class SeedService:
    KEYWORDS = {
        "ads": ["quảng cáo", "bán", "sale", "marketing"],
        "email": ["email", "gửi mail", "thư"],
        "blog": ["blog", "viết bài", "seo"],
    }

    def _detect_intent(self, text: str) -> str:
        text_low = text.lower()

        for intent, keywords in self.KEYWORDS.items():
            if any(k in text_low for k in keywords):
                return intent

        return "unknown"

    def _normalize(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def run(self, seed: dict) -> SeedOutput:

        raw = seed.get("raw_input", "")

        normalized = self._normalize(raw)

        intent = self._detect_intent(normalized)

        try:
            lang = detect(normalized)
        except:
            lang = "vi"

        return SeedOutput(
            raw_input=raw,
            normalized_input=normalized,
            intent=intent,
            language=lang,
            brand_color=seed.get("brand_color", "#000000"),
            confidence=0.7 if intent != "unknown" else 0.3,
        )
