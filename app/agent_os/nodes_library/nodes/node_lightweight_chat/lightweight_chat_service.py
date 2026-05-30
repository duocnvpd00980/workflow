import os
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader
from agent_os.nodes_library.node_lightweight_chat.lightweight_chat_protocol import (
    LightweightChatOutput,
)


class LightweightChatService:
    def __init__(self, llm_engine: Any):
        self._llm = llm_engine
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self._env = Environment(loader=FileSystemLoader(current_dir))

    async def run(
        self, user_input: str, context: Dict[str, Any]
    ) -> LightweightChatOutput:
        # Load template
        template = self._env.get_template("lightweight_chat.jinja2")
        prompt = template.render(
            user_input=user_input, context=context, is_fallback=False
        )

        try:
            result = await self._llm.generate(
                system=prompt,  # Prompt đã được tối ưu hóa
                user="Generate response.",
                schema=LightweightChatOutput,
                temperature=0.6,
            )

            # Trả về Pydantic Object đã được validate
            return LightweightChatOutput(response=result.response, tone=result.tone)

        except Exception as e:
            # Ghi log lỗi để dev check
            print(f"[ERROR][LightweightChat] LLM Failed: {e}")

            # Trả về "Hợp đồng dữ liệu an toàn" (Graceful Fallback)
            return LightweightChatOutput(
                response="Rất xin lỗi, hệ thống đang gặp chút gián đoạn. Tôi có thể giúp gì cho bạn?",
                tone="neutral",
            )
