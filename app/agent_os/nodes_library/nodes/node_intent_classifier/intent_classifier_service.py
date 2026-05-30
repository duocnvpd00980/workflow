# =========================================================
# FILE: intent_classifier_service.py
# =========================================================
from typing import Any, Final
import asyncio
import litellm
from pydantic import Field
from semantic_router import Route
from semantic_router.routers import SemanticRouter
from semantic_router.encoders.base import DenseEncoder

from .intent_classifier_protocol import IntentClassifierOutput


# 1. ENCODER
class SystemFactoryEncoder(DenseEncoder):
    model: str = Field(...)
    base_url: str = Field(...)

    def __init__(self, factory_embed_engine: Any, **kwargs):
        super().__init__(
            name="intent-router-encoder",
            model=factory_embed_engine.model,
            base_url=factory_embed_engine.base_url,
            **kwargs,
        )

    def __call__(self, docs: list[str]) -> list[list[float]]:
        if not docs:
            return []
        response = litellm.embedding(
            model=self.model, input=docs, api_base=self.base_url
        )
        return [x["embedding"] for x in response["data"]]


# 2. SERVICE
class IntentClassifierService:
    SYSTEM_PROMPT: Final[str] = """
Bạn là Intent Classifier chuyên nghiệp. Chỉ được chọn 1 trong 3 mode: "marketing", "qa", "smalltalk".
QUY TẮC:
1. Trả về JSON đúng cấu trúc: {"mode": "string", "confidence": float, "requires_memory": bool, "requires_knowledge": bool}
2. Không giải thích, không thêm text thừa.
3. Nếu không chắc chắn, hãy mặc định mode="qa".
"""
    MIN_ROUTE_SCORE: Final[float] = 0.62

    def __init__(self, ollama_embed_model: Any, llm_engine: Any):
        self._llm = llm_engine
        self._marketing_keywords = {
            "ads",
            "seo",
            "campaign",
            "facebook",
            "google",
            "content",
            "sale",
            "marketing",
        }
        self._smalltalk_keywords = {
            "hello",
            "hi",
            "buồn",
            "mệt",
            "chào",
            "tán dóc",
            "khỏe không",
        }
        self._qa_keywords = {
            "là gì",
            "giải thích",
            "how to",
            "explain",
            "tại sao",
            "định nghĩa",
            "hướng dẫn",
        }

        routes = [
            Route(
                name="marketing",
                utterances=[
                    "quảng cáo",
                    "facebook ads",
                    "content",
                    "campaign",
                    "landing page",
                ],
            ),
            Route(
                name="smalltalk",
                utterances=["hello", "hi", "xin chào", "buồn quá", "tán dóc"],
            ),
            Route(
                name="qa",
                utterances=[
                    "là gì",
                    "giải thích",
                    "hướng dẫn sử dụng",
                    "làm thế nào để",
                ],
            ),
        ]

        self._router = SemanticRouter(
            encoder=SystemFactoryEncoder(factory_embed_engine=ollama_embed_model),
            routes=routes,
            auto_sync="local",
        )

    async def run_classification(self, user_text: str) -> IntentClassifierOutput:
        cleaned_text = str(user_text or "").strip()
        if not cleaned_text:
            return self._build_output("qa", 0.0)

        lowered = cleaned_text.lower()

        # FAST PATH
        if any(k in lowered for k in self._marketing_keywords):
            return self._build_output("marketing", 0.95)
        if any(k in lowered for k in self._smalltalk_keywords):
            return self._build_output("smalltalk", 0.95)
        if any(k in lowered for k in self._qa_keywords):
            return self._build_output("qa", 0.95)

        # SEMANTIC ROUTER
        try:
            router_output = await asyncio.to_thread(self._router, cleaned_text)
            if router_output and router_output.name:
                score = float(getattr(router_output, "score", 0.0))
                if score >= self.MIN_ROUTE_SCORE:
                    return self._build_output(router_output.name, score)
        except Exception as e:
            print(f"[WARN][ROUTER] {e}")

        # LLM FALLBACK (Bọc giáp an toàn)
        try:
            print(f"[DEBUG][LLM FALLBACK] Gọi LLM cho: '{cleaned_text}'")
            result: IntentClassifierOutput = await self._llm.generate(
                system=self.SYSTEM_PROMPT,
                user=cleaned_text,
                schema=IntentClassifierOutput,
                temperature=0.0,
            )
            return self._build_output(result.mode, result.confidence)
        except Exception as e:
            print(f"[ERROR][LLM FALLBACK] {e}. Tự động fallback về 'qa'.")
            return self._build_output("qa", 0.45)

    def _build_output(self, mode: str, confidence: float) -> IntentClassifierOutput:
        mapping = {
            "marketing": IntentClassifierOutput(
                mode="marketing",
                confidence=confidence,
                requires_memory=True,
                requires_knowledge=True,
            ),
            "smalltalk": IntentClassifierOutput(
                mode="smalltalk",
                confidence=confidence,
                requires_memory=False,
                requires_knowledge=False,
            ),
            "qa": IntentClassifierOutput(
                mode="qa",
                confidence=confidence,
                requires_memory=False,
                requires_knowledge=True,
            ),
        }
        return mapping.get(
            mode.lower().strip(), IntentClassifierOutput(mode="qa", confidence=0.45)
        )
