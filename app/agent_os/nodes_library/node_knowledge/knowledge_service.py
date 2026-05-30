from __future__ import annotations
import logging
import os
from typing import Any
from jinja2 import Environment, FileSystemLoader

from agent_os.nodes_library.node_knowledge.knowledge_protocol import HypotheticalDocOutput

logger = logging.getLogger(__name__)

class KnowledgeService:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self._env = Environment(loader=FileSystemLoader(current_dir))

    async def run(self, user_input: str,  llm_engine: Any,) -> str:

        # Tối ưu: Nếu query đã đủ chi tiết, không dùng HyDE để tiết kiệm VRAM
        if len(user_input.split()) >= 8:
            return user_input

        try:
            # Render prompt từ template
            template = self._env.get_template("knowledge_prompt.jinja2")
            system_prompt = template.render(user_input=user_input)
            
            raw_response = await llm_engine.generate(
                system=system_prompt,
                user=user_input,                  
                schema=HypotheticalDocOutput,
                temperature=0.0,
            )
            
            text_content = str(raw_response)
            logger.debug("[HyDE] HyDE generation successful.")
            return f"{user_input} {text_content}"
            
        except Exception as e:
            logger.error("[HyDE] HyDE generation failed: %s", e)
            return user_input

class KnowledgeRetrieverService:
    def __init__(self, score_threshold: float = 0.45) -> None:
        self._score_threshold = score_threshold

    def process_retrieved_chunks(self, raw_chunks: Any) -> dict:
        """Lọc và chuẩn hóa dữ liệu từ vector store."""
        if not isinstance(raw_chunks, list):
            return {"contexts": [], "score_threshold": self._score_threshold}
            
        contexts = []
        for chunk in raw_chunks:
            # Dùng getattr để tránh lỗi khi chunk không có thuộc tính
            score = getattr(chunk, 'score', 0.0) or 0.0
            if score < self._score_threshold:
                continue
                
            contexts.append({
                "text": getattr(chunk, 'text', ""),
                "score": score,
                "source_id": getattr(chunk, 'metadata', {}).get("source_id", "N/A")
            })
            
        return {
            "contexts": contexts,
            "score_threshold": self._score_threshold
        }