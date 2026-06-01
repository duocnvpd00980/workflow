from __future__ import annotations
import logging
import os

from jinja2 import Environment, FileSystemLoader
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from .generation_protocol import GenerationOutput

logger = logging.getLogger(__name__)


class GenerationService:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self._env = Environment(loader=FileSystemLoader(current_dir))

    async def run(
        self,
        user_input: str,
        chat_history: list[dict],
        rag_context: str,
        llm: BaseChatModel,
    ) -> GenerationOutput:

        rag_context = (rag_context or "").strip()

        formatted_history = [
            {"type": m["role"], "content": m["content"]}
            for m in chat_history
            if m.get("content", "").strip()
            and m.get("role", "user") in {"user", "assistant", "system"}
        ]

        system_prompt = self._env.get_template("generation.jinja2").render(
            chat_history=formatted_history,
            rag_context=rag_context,
            extra_rules=[],
        )

        messages = [SystemMessage(content=system_prompt)]
        for m in formatted_history:
            if m["type"] == "user":
                messages.append(HumanMessage(content=m["content"]))
            elif m["type"] == "assistant":
                messages.append(AIMessage(content=m["content"]))
        messages.append(HumanMessage(content=user_input))

        try:
            result = await llm.ainvoke(messages)
            response_text = (result.content or "").strip()

            if not response_text:
                raise ValueError("LLM returned empty response")

            usage = getattr(result, "usage_metadata", None) or {}
            return GenerationOutput(
                response=response_text,
                tone="neutral",
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
            )

        except Exception:
            logger.exception("[GenerationService] failed")
            return GenerationOutput(
                response="Tôi chưa thể tạo phản hồi lúc này.",
                tone="neutral",
                input_tokens=0,
                output_tokens=0,
            )