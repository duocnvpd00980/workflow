from typing import Any
from .router_protocol import RouterOutput


class RouterService:
    """
    CORE DOMAIN: Phân tích ý định và điều hướng luồng công việc.
    """

    SYSTEM_PROMPT = """
    You are a Strategic Router for a Marketing Agency.
    Determine the correct execution path.

    RULES:
    - "ads_only": social media ads content (Facebook, Google Ads)
    - "blog_only": SEO articles, blog posts
    - "email_only": email content, promotional email, newsletters
    - "full_campaign": multi deliverables (e.g., both email and ads)
    - "invalid": out of scope or ambiguous

    CRITICAL: "email quảng cáo" must be classified as "email_only".
    You MUST strictly return the JSON matching the required schema.
    """

    def __init__(self, llm_engine: Any):
        self._llm = llm_engine

    async def classify(self, user_input: str, context: dict) -> RouterOutput:

        try:
            result = await self._llm.generate(
                system=self.SYSTEM_PROMPT,
                user=f"""
                User Brief: {user_input}
                Context: {context}
                """,
                schema=RouterOutput,
                temperature=0.1
            )

            # SAFETY WRAP (IMPORTANT)
            return RouterOutput(
                intent=getattr(result, "intent", "invalid"),
                reasoning=getattr(result, "reasoning", "auto"),
                confidence_score=getattr(result, "confidence_score", 0.0),
                next_steps=getattr(result, "next_steps", []),
            )

        except Exception:
            return RouterOutput(
                intent="invalid",
                reasoning="fallback due to error",
                confidence_score=0.0,
                next_steps=[],
            )