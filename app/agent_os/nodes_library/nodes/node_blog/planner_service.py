from typing import Any, Final
from .planner_schema import BlogPlan

class PlannerService:
    SYSTEM_PROMPT: Final[str] = """
You are an expert Content Strategist. 
Your task is to create a detailed outline for a high-performing blog post based on the user's topic.
Ensure the structure is SEO-friendly and engaging.
"""

    def __init__(self, llm_engine: Any):
        self._llm = llm_engine

    async def run(self, topic: str, language: str = "vi") -> BlogPlan:
        return await self._llm.generate(
            system=self.SYSTEM_PROMPT,
            user=f"Create a blog plan for topic: {topic} in {language}",
            schema=BlogPlan,
            temperature=0.3, # Thấp hơn để có cấu trúc chặt chẽ
        )