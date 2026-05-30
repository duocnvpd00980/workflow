import os
from typing import Any
from jinja2 import Environment, FileSystemLoader
from .lightweight_chat_protocol import LightweightChatOutput


class LightweightChatService:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self._env = Environment(loader=FileSystemLoader(current_dir))

    async def run(
        self,
        user_input: str,
        llm_engine: Any,
    ) -> LightweightChatOutput:

        template = self._env.get_template("lightweight_chat.jinja2")
        prompt = template.render(user_input=user_input)

        try:
            result = await llm_engine.generate(
                system=prompt,
                user=user_input,
                schema=LightweightChatOutput,
                temperature=0.7,
            )
            return LightweightChatOutput(
                response=result.response,
                tone=result.tone,
            )

        except Exception as e:
            return LightweightChatOutput(
                response="Rất xin lỗi, hệ thống đang gặp chút gián đoạn. Tôi có thể giúp gì cho bạn?",
                tone="neutral",
            )
