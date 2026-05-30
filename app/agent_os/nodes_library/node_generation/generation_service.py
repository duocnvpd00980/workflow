import logging
import os
from typing import Any

from jinja2 import Environment, FileSystemLoader

from .generation_protocol import GenerationOutput

logger = logging.getLogger(__name__)


class GenerationService:

    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self._env = Environment(
            loader=FileSystemLoader(current_dir)
        )

    async def run(
        self,
        user_input: str,
        chat_history: list[dict],
        rag_context: str,
        llm_engine: Any,
    ) -> GenerationOutput:

        rag_context = (rag_context or "").strip()

        formatted_history = []

        for msg in chat_history:

            role = str(
                msg.get("role", "user")
            ).strip().lower()

            content = str(
                msg.get("content", "")
            ).strip()

            if not content:
                continue

            if role not in {
                "user",
                "assistant",
                "system",
            }:
                role = "user"

            formatted_history.append({
                "type": role,
                "content": content,
            })

        prompt = self._env.get_template(
            "generation.jinja2"
        ).render(
            chat_history=formatted_history,
            rag_context=rag_context,
            extra_rules=[],
        )

        try:

            result = await llm_engine.generate_raw(
                system=prompt,
                user=user_input,
                temperature=0.2,
                max_tokens=1024,
            )

            logger.debug(
                "RAW RESULT TYPE: %s",
                type(result),
            )

            logger.debug(
                "RAW RESULT: %s",
                result,
            )

            response_text = ""

            if isinstance(result, str):
                response_text = result

            elif isinstance(result, dict):
                response_text = (
                    result.get("response")
                    or result.get("content")
                    or result.get("text")
                    or ""
                )

            else:
                response_text = (
                    getattr(result, "response", None)
                    or getattr(result, "content", None)
                    or getattr(result, "text", None)
                    or ""
                )

            response_text = str(
                response_text
            ).strip()

            if not response_text:
                raise ValueError(
                    "LLM returned empty response"
                )

            return GenerationOutput(
                response=response_text,
                tone="neutral",
                input_tokens=getattr(
                    result,
                    "input_tokens",
                    0,
                ),
                output_tokens=getattr(
                    result,
                    "output_tokens",
                    0,
                ),
            )

        except Exception:
            logger.exception(
                "[GenerationService] Failed to generate response"
            )

            return GenerationOutput(
                response=(
                    "Tôi chưa thể tạo phản hồi lúc này."
                ),
                tone="neutral",
                input_tokens=0,
                output_tokens=0,
            )

