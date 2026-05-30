from typing import Any, Final
from .polisher_schema import FinalProduct

class PolisherService:
    SYSTEM_PROMPT: Final[str] = """
    You are a Content Editor & Formatter. 
    Task: Take the provided blog, ads, and email content and format them into a single, beautiful Markdown document.
    
    RULES:
    1. Use clear H1, H2, H3 headers.
    2. Use bolding for emphasis and bullet points for readability.
    3. Ensure the tone is consistent across all parts.
    4. Fix any lingering grammar or spacing issues.
    5. Add relevant emojis to make it engaging.
    """

    def __init__(self, llm_engine: Any):
        self._llm = llm_engine

    async def run(self, blog: str, ads: Any, mail: Any) -> FinalProduct:
        user_msg = f"""
        Please polish and combine these:
        --- BLOG POST ---
        {blog}
        
        --- AD COPIES ---
        {ads}
        
        --- EMAIL CAMPAIGN ---
        {mail}
        """
        
        return await self._llm.generate(
            system=self.SYSTEM_PROMPT,
            user=user_msg,
            schema=FinalProduct,
            temperature=0.5
        )