from typing import Any, Final
from .planner_protocol import BlogPlan

class PlannerService:
    """
    CORE DOMAIN: Chỉ chứa logic lập kế hoạch.
    Nó giống như Driver điều khiển con chip, không quan tâm nó đang cắm vào Mainboard nào.
    """
    SYSTEM_PROMPT: Final[str] = """
    You are an expert Content Strategist. 
    Create a detailed SEO-friendly blog outline.
    """

    def __init__(self, llm_engine: Any):
        self._llm = llm_engine

    async def run(self, topic: str, language: str = "vi") -> BlogPlan:
        # Tương tác với LLM thông qua Engine được cấp phát
        return await self._llm.generate(
            system=self.SYSTEM_PROMPT,
            user=f"Topic: {topic} | Language: {language}",
            schema=BlogPlan,
            temperature=0.3
        )