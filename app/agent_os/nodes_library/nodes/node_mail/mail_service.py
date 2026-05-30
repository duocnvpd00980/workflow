from typing import Any, Dict, Final
from .mail_protocol import convertToEmailCampaign


class EmailService:
    """
    CORE DOMAIN: Logic viết Email Marketing.
    """

    SYSTEM_PROMPT: Final[str] = """
You are an expert Email Marketer.
Your task is to convert an Ad Copy into a compelling Email Campaign.

STRICT RULES:
1. You MUST respond by calling the function 'convertToEmailCampaign'. 
2. DO NOT use any other function name (like 'convertToEmailCampaign').
3. Always return valid JSON matching the schema.
4. Tone: Professional yet persuasive.
5. Ensure the Subject Line is catchy and the body has a clear CTA.
"""

    def __init__(self, llm_engine: Any):
        self._llm = llm_engine

    async def run(self, seed: Dict[str, Any]) -> convertToEmailCampaign:
        """Dựa trên nội dung Ads để tạo Email"""
        return await self._llm.generate(
            system=self.SYSTEM_PROMPT,
            user=f"Context from Ads: {seed.get('ads_content')}. Session: {seed.get('session_id')}",
            schema=convertToEmailCampaign,
            # Giảm temperature một chút giúp model bớt "sáng tạo" tên hàm
            temperature=0.3,
        )
