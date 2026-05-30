# =============================================================================
# FILE: intent_classifier_service.py
# =============================================================================

import re
import asyncio
from typing import Any, Final
from cachetools import TTLCache

import litellm

from semantic_router import Route
from semantic_router.routers import SemanticRouter
from semantic_router.encoders.base import DenseEncoder

from pydantic import Field

from .intent_classifier_protocol import IntentClassifierOutput


# =============================================================================
# ENCODER
# =============================================================================


class SystemFactoryEncoder(DenseEncoder):
    model: str = Field(...)
    base_url: str = Field(...)

    def __init__(
        self,
        factory_embed_engine: Any,
        **kwargs,
    ):
        super().__init__(
            name="semantic-intent-router",
            model=factory_embed_engine.model,
            base_url=factory_embed_engine.base_url,
            **kwargs,
        )

    def __call__(self, docs: list[str]) -> list[list[float]]:

        if not docs:
            return []

        response = litellm.embedding(
            model=self.model,
            input=docs,
            api_base=self.base_url,
        )

        return [x["embedding"] for x in response["data"]]


# =============================================================================
# SERVICE
# =============================================================================


class IntentClassifierService:
    MIN_ROUTE_SCORE: Final[float] = 0.70

    # -------------------------------------------------------------------------
    # INIT
    # -------------------------------------------------------------------------

    def __init__(
        self,
        ollama_embed_model: Any,
    ):

        self._cache = TTLCache(
            maxsize=5000,
            ttl=3600,
        )

        # ---------------------------------------------------------------------
        # RULES
        # ---------------------------------------------------------------------

        self._marketing_keywords = {
            "ads",
            "seo",
            "campaign",
            "facebook ads",
            "google ads",
            "landing page",
            "marketing",
            "content",
            "sale",
        }

        self._coding_keywords = {
            "python",
            "react",
            "nextjs",
            "bug",
            "fix",
            "typescript",
            "javascript",
            "api",
            "flask",
            "fastapi",
            "docker",
            "sql",
            "postgres",
        }

        self._research_keywords = {
            "research",
            "analyze",
            "phân tích",
            "nghiên cứu",
            "compare",
            "benchmark",
        }

        self._math_keywords = {
            "solve",
            "equation",
            "math",
            "integral",
            "đạo hàm",
            "tính",
        }

        self._translation_keywords = {
            "translate",
            "dịch",
            "translation",
        }

        self._smalltalk_keywords = {
            "hello",
            "hi",
            "sad",
            "buồn",
            "mệt",
            "chào",
        }

        # ---------------------------------------------------------------------
        # ROUTES
        # ---------------------------------------------------------------------

        routes = [
            # CODING
            Route(
                name="coding",
                utterances=[
                    "fix my python code",
                    "react hydration error",
                    "typescript issue",
                    "docker container problem",
                    "build api with flask",
                    "postgres query optimization",
                    "nextjs routing problem",
                ],
            ),
            # MARKETING
            Route(
                name="marketing",
                utterances=[
                    "create facebook ads campaign",
                    "seo content strategy",
                    "marketing funnel",
                    "landing page copy",
                    "google ads campaign",
                    "email marketing plan",
                ],
            ),
            # RESEARCH
            Route(
                name="research",
                utterances=[
                    "research ai market",
                    "compare technologies",
                    "deep analysis",
                    "benchmark frameworks",
                    "industry analysis",
                ],
            ),
            # QA
            Route(
                name="qa",
                utterances=[
                    "what is",
                    "explain",
                    "how does it work",
                    "guide me",
                    "definition",
                    "tutorial",
                ],
            ),
            # MATH
            Route(
                name="math",
                utterances=[
                    "solve equation",
                    "calculate integral",
                    "math problem",
                    "statistics problem",
                ],
            ),
            # TRANSLATION
            Route(
                name="translation",
                utterances=[
                    "translate this",
                    "dịch sang tiếng anh",
                    "dịch giúp tôi",
                ],
            ),
            # SMALLTALK
            Route(
                name="smalltalk",
                utterances=[
                    "hello",
                    "hi",
                    "sad today",
                    "i am tired",
                    "xin chào",
                ],
            ),
        ]

        # ---------------------------------------------------------------------
        # ROUTER
        # ---------------------------------------------------------------------

        encoder = SystemFactoryEncoder(factory_embed_engine=ollama_embed_model)

        self._router = SemanticRouter(
            encoder=encoder,
            routes=routes,
            auto_sync="local",
        )

    # =========================================================================
    # MAIN
    # =========================================================================

    async def run_classification(
        self,
        user_text: str,
    ) -> IntentClassifierOutput:

        text = self._normalize_text(user_text)

        if not text:
            return self._build_unknown()

        # ---------------------------------------------------------------------
        # CACHE
        # ---------------------------------------------------------------------

        cached = self._cache.get(text)

        if cached:
            return cached

        # ---------------------------------------------------------------------
        # FAST RULES
        # ---------------------------------------------------------------------

        fast_result = self._fast_rule_classification(text)

        if fast_result:
            self._cache[text] = fast_result
            return fast_result

        # ---------------------------------------------------------------------
        # SEMANTIC ROUTER
        # ---------------------------------------------------------------------

        try:
            router_output = await asyncio.to_thread(
                self._router,
                text,
            )

            if router_output and router_output.name:
                score = float(getattr(router_output, "score", 0.0) or 0.0)

                if score >= self.MIN_ROUTE_SCORE:
                    result = self._build_by_route(
                        mode=router_output.name,
                        confidence=score,
                        text=text,
                    )

                    self._cache[text] = result

                    return result

        except Exception as e:
            print(f"[ROUTER ERROR] {e}")

        # ---------------------------------------------------------------------
        # FALLBACK
        # ---------------------------------------------------------------------

        result = self._fallback_policy(text)

        self._cache[text] = result

        return result

    # =========================================================================
    # FAST RULES
    # =========================================================================

    def _fast_rule_classification(
        self,
        text: str,
    ) -> IntentClassifierOutput | None:

        if any(k in text for k in self._coding_keywords):
            return self._build_by_route(
                mode="coding",
                confidence=0.95,
                text=text,
            )

        if any(k in text for k in self._marketing_keywords):
            return self._build_by_route(
                mode="marketing",
                confidence=0.95,
                text=text,
            )

        if any(k in text for k in self._research_keywords):
            return self._build_by_route(
                mode="research",
                confidence=0.90,
                text=text,
            )

        if any(k in text for k in self._math_keywords):
            return self._build_by_route(
                mode="math",
                confidence=0.90,
                text=text,
            )

        if any(k in text for k in self._translation_keywords):
            return self._build_by_route(
                mode="translation",
                confidence=0.95,
                text=text,
            )

        if any(k in text for k in self._smalltalk_keywords):
            return self._build_by_route(
                mode="smalltalk",
                confidence=0.95,
                text=text,
            )

        return None

    # =========================================================================
    # ROUTE POLICY
    # =========================================================================

    def _build_by_route(
        self,
        mode: str,
        confidence: float,
        text: str,
    ) -> IntentClassifierOutput:

        complexity = self._detect_complexity(text)

        # ---------------------------------------------------------------------
        # POLICY TABLE
        # ---------------------------------------------------------------------

        policy_map = {
            "coding": {
                "execution_strategy": "tools",
                "model_tier": "reasoning",
                "requires_memory": True,
                "requires_knowledge": True,
                "requires_tools": True,
                "requires_web_search": False,
                "requires_rag": False,
            },
            "research": {
                "execution_strategy": "multi_agent",
                "model_tier": "reasoning",
                "requires_memory": True,
                "requires_knowledge": True,
                "requires_tools": True,
                "requires_web_search": True,
                "requires_rag": True,
            },
            "marketing": {
                "execution_strategy": "multi_agent",
                "model_tier": "balanced",
                "requires_memory": True,
                "requires_knowledge": True,
                "requires_tools": False,
                "requires_web_search": True,
                "requires_rag": False,
            },
            "qa": {
                "execution_strategy": "direct",
                "model_tier": "balanced",
                "requires_memory": False,
                "requires_knowledge": True,
                "requires_tools": False,
                "requires_web_search": False,
                "requires_rag": False,
            },
            "math": {
                "execution_strategy": "tools",
                "model_tier": "reasoning",
                "requires_memory": False,
                "requires_knowledge": False,
                "requires_tools": True,
                "requires_web_search": False,
                "requires_rag": False,
            },
            "translation": {
                "execution_strategy": "direct",
                "model_tier": "cheap",
                "requires_memory": False,
                "requires_knowledge": False,
                "requires_tools": False,
                "requires_web_search": False,
                "requires_rag": False,
            },
            "smalltalk": {
                "execution_strategy": "direct",
                "model_tier": "cheap",
                "requires_memory": True,
                "requires_knowledge": False,
                "requires_tools": False,
                "requires_web_search": False,
                "requires_rag": False,
            },
        }

        config = policy_map.get(mode)

        if not config:
            return self._build_unknown()

        return IntentClassifierOutput(
            mode=mode,
            complexity=complexity,
            confidence=confidence,
            **config,
        )

    # =========================================================================
    # COMPLEXITY
    # =========================================================================

    def _detect_complexity(
        self,
        text: str,
    ) -> str:

        word_count = len(text.split())

        if word_count <= 8:
            return "simple"

        if word_count <= 25:
            return "medium"

        return "deep"

    # =========================================================================
    # NORMALIZE
    # =========================================================================

    def _normalize_text(
        self,
        text: str,
    ) -> str:

        text = str(text or "").lower().strip()

        text = re.sub(r"\s+", " ", text)

        return text

    # =========================================================================
    # FALLBACK
    # =========================================================================

    def _fallback_policy(
        self,
        text: str,
    ) -> IntentClassifierOutput:

        if len(text.split()) > 20:
            return self._build_by_route(
                mode="research",
                confidence=0.50,
                text=text,
            )

        return self._build_by_route(
            mode="qa",
            confidence=0.50,
            text=text,
        )

    # =========================================================================
    # UNKNOWN
    # =========================================================================

    def _build_unknown(
        self,
    ) -> IntentClassifierOutput:

        return IntentClassifierOutput(
            mode="unknown",
            complexity="simple",
            execution_strategy="direct",
            model_tier="cheap",
            requires_memory=False,
            requires_knowledge=False,
            requires_tools=False,
            requires_web_search=False,
            requires_rag=False,
            confidence=0.0,
        )
