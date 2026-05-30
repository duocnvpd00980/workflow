from __future__ import annotations
import logging
import os
from typing import Any
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class HyDEService:
    def __init__(self, llm_engine: Any):
        self._llm = llm_engine
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self._env = Environment(loader=FileSystemLoader(current_dir))
        self._template = self._env.get_template("hyde_prompt.jinja2")

    async def run(self, query: str) -> str:
        # Tối ưu: Nếu query đã đủ chi tiết, không dùng HyDE để tiết kiệm VRAM
        if len(query.split()) >= 8:
            return query

        try:
            # Render prompt từ template
            prompt_content = self._template.render(query=query)

            # Gọi LLM với tham số schema=None (bỏ qua JSON validation cứng nhắc)
            # Dùng 'ollama/' prefix để định tuyến đúng tới Ollama
            raw_response = await self._llm.generate(
                prompt=prompt_content,
                model="ollama/deepseek-r1:1.5b",
                schema=None,
                temperature=0.3,
            )

            text_content = str(raw_response)
            logger.debug("[HyDE] HyDE generation successful.")
            return f"{query} {text_content}"

        except Exception as e:
            logger.error("[HyDE] HyDE generation failed: %s", e)
            return query


class QARetrieverService:
    def __init__(self, score_threshold: float = 0.45) -> None:
        self._score_threshold = score_threshold

    def process_retrieved_chunks(self, raw_chunks: Any) -> dict:
        """Lọc và chuẩn hóa dữ liệu từ vector store."""
        if not isinstance(raw_chunks, list):
            return {"contexts": [], "score_threshold": self._score_threshold}

        contexts = []
        for chunk in raw_chunks:
            # Dùng getattr để tránh lỗi khi chunk không có thuộc tính
            score = getattr(chunk, "score", 0.0) or 0.0
            if score < self._score_threshold:
                continue

            contexts.append(
                {
                    "text": getattr(chunk, "text", ""),
                    "score": score,
                    "source_id": getattr(chunk, "metadata", {}).get("source_id", "N/A"),
                }
            )

        return {"contexts": contexts, "score_threshold": self._score_threshold}
