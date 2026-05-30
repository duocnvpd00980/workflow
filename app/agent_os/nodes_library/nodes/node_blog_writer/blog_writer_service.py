from typing import Any, Final
from .blog_writer_protocol import WriterOutput


class WriterService:
    SYSTEM_PROMPT: Final[str] = """
    You are a professional Content Writer.
    Task: Write a full blog post based on the provided Plan.
    
    CRITICAL RULE:
    If the plan requires specific facts, dates, or technical data that you are unsure of, 
    set 'pending_tool' to True and provide a 'tool_query'.
    Otherwise, write the full content and set 'pending_tool' to False.
    """

    def __init__(self, llm_engine: Any):
        self._llm = llm_engine

    async def run(
        self, plan: Any, tool_data: str = "", lang: str = "vi"
    ) -> WriterOutput:
        user_msg = f"Plan: {plan}\nExisting Data: {tool_data}\nLanguage: {lang}"

        return await self._llm.generate(
            system=self.SYSTEM_PROMPT,
            user=user_msg,
            schema=WriterOutput,
            temperature=0.7,  # Tăng độ sáng tạo cho Writer
        )
