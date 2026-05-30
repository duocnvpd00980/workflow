"""
agent_os/system/runtime/runtime_engine.py
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol, TypeVar, runtime_checkable

import instructor
import litellm
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Load OPENROUTER_API_KEY — đọc thẳng từ .env nếu chưa có trong os.environ
# Django-environ load vào os.environ khi settings được import, nhưng
# _bootstrap() có thể chạy trước khi settings hoàn tất trong một số context.
# ---------------------------------------------------------------------------
if not os.environ.get("OPENROUTER_API_KEY"):
    _env_file = Path(__file__).resolve().parents[4] / ".env"
    if _env_file.exists():
        for _line in _env_file.read_text().splitlines():
            if _line.startswith("OPENROUTER_API_KEY="):
                os.environ["OPENROUTER_API_KEY"] = _line.split("=", 1)[1].strip()
                break

if os.environ.get("OPENROUTER_API_KEY"):
    litellm.openrouter_api_key = os.environ["OPENROUTER_API_KEY"]

if os.environ.get("OPENAI_API_KEY"):
    litellm.api_key = os.environ["OPENAI_API_KEY"]

# ---------------------------------------------------------------------------
T = TypeVar("T", bound=BaseModel)
_OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://192.168.101.18:11434")
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


@runtime_checkable
class LLMEngine(Protocol):
    async def generate(self, *, system: str, user: str, schema: type[T], temperature: float = 0.3) -> T: ...


@runtime_checkable
class EmbeddingEngine(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class LiteLLMEngine:
    def __init__(self, model: str, base_url: str | None = None, max_retries: int = 3) -> None:
        self.model = model
        self.base_url = base_url
        self.max_retries = max_retries
        self._client = instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.JSON)

    async def generate(self, *, system: str, user: str, schema: type[T], temperature: float = 0.3) -> T:
        api_base = _OPENROUTER_BASE if self.model.startswith("openrouter/") else self.base_url
        api_key = None
        if self.model.startswith("openrouter/"):
            api_key = os.environ.get("OPENROUTER_API_KEY")
        return await self._client.chat.completions.create(
            model=self.model,
            response_model=schema,
            temperature=temperature,
            max_retries=self.max_retries,
            api_base=api_base,
            api_key=api_key,
            stop=["Thinking Process:"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    async def generate_raw(self, *, system: str, user: str, temperature: float = 0.0, max_tokens: int = 10) -> str:
        """HÀM THÊM MỚI: Gọi LLM sinh text tự do, tối ưu cho model nhỏ (Qwen 0.5B) không bị loop token."""
        api_base = _OPENROUTER_BASE if self.model.startswith("openrouter/") else self.base_url
        
        # Đồng bộ hóa cấu hình endpoint gọi sang Ollama
        response = await litellm.acompletion(
            model=self.model,
            temperature=temperature,
            api_base=api_base,
            max_tokens=max_tokens,
            stop=["Thinking Process:"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


class LiteEmbeddingEngine:
    def __init__(self, model: str, base_url: str | None = None) -> None:
        self.model = model
        self.base_url = base_url

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        api_base = _OPENROUTER_BASE if self.model.startswith("openrouter/") else self.base_url
        response = await litellm.aembedding(model=self.model, input=texts, api_base=api_base)
        return [item["embedding"] for item in response["data"]]


class LLMFactory:
    def __init__(self, llm_engines: dict[str, LiteLLMEngine], embed_engines: dict[str, LiteEmbeddingEngine]) -> None:
        self._llm = llm_engines
        self._embed = embed_engines

    def get_model(self, key: str = "default") -> LiteLLMEngine:
        engine = self._llm.get(key)
        if engine is not None:
            return engine
        fallback = self._llm.get("default") or next(iter(self._llm.values()), None)
        if fallback is None:
            raise RuntimeError("LLMFactory has no engines registered.")
        return fallback

    def get_embedding(self, key: str = "default_embed") -> LiteEmbeddingEngine:
        engine = self._embed.get(key)
        if engine is not None:
            return engine
        fallback = self._embed.get("default_embed") or next(iter(self._embed.values()), None)
        if fallback is None:
            raise RuntimeError("LLMFactory has no embedding engines registered.")
        return fallback


def build_runtime() -> dict[str, Any]:
    llm_engines: dict[str, LiteLLMEngine] = {
        "default":          LiteLLMEngine(model="ollama/qwen3:0.6b",      base_url=_OLLAMA_BASE),
        "qwen2.5":          LiteLLMEngine(model="ollama/qwen2.5:3b",      base_url=_OLLAMA_BASE),
        "qwen2.5-1.5b":     LiteLLMEngine(model="ollama/deepseek-r1:1.5b",   base_url=_OLLAMA_BASE),
        "llama3.1":         LiteLLMEngine(model="ollama/llama3.1:8b",     base_url=_OLLAMA_BASE),
        "router":           LiteLLMEngine(model="ollama/qwen2.5:7b",      base_url=_OLLAMA_BASE, max_retries=5),
        "premium":          LiteLLMEngine(model="openai/gpt-4o"),
        "cloud_qwen":       LiteLLMEngine(model="openrouter/qwen/qwen3-80b:free"),
        "cloud_router":     LiteLLMEngine(model="openrouter/deepseek/deepseek-v4-flash:free", max_retries=5),
        "cloud_thinking":   LiteLLMEngine(model="openrouter/arcee/trinity-large-thinking:free"),
        "cloud_llama":      LiteLLMEngine(model="openrouter/nousresearch/hermes-3-405b-instruct:free"),
        "cloud_premium":    LiteLLMEngine(model="openrouter/openai/gpt-oss-120b:free"),
        "cloud_gemma":      LiteLLMEngine(model="openrouter/google/gemma-4-31b:free"),
        "cloud_glm":        LiteLLMEngine(model="openrouter/z-ai/glm-4.5-air:free"),
        "cloud_deepseek":   LiteLLMEngine(model="openrouter/deepseek/deepseek-v4-flash:free"),
        "cloud_uncensored": LiteLLMEngine(model="openrouter/venice/uncensored:free"),
    }

    embed_engines: dict[str, LiteEmbeddingEngine] = {
        "default_embed":      LiteEmbeddingEngine(model="ollama/nomic-embed-text:latest", base_url=_OLLAMA_BASE),
        "cloud_router_embed": LiteEmbeddingEngine(model="ollama/all-minilm",              base_url=_OLLAMA_BASE),
        "cloud_embed":        LiteEmbeddingEngine(model="ollama/text-embedding-3-small",  base_url=_OLLAMA_BASE),
    }

    return {"llm_factory": LLMFactory(llm_engines, embed_engines)}


class BaseModule:
    def __init__(self, llm_factory: LLMFactory, model_type: str = "default",
                 system_prompt: str = "", schema: type[BaseModel] | None = None) -> None:
        self._llm = llm_factory.get_model(model_type)
        self.system_prompt = system_prompt
        self.schema = schema

    async def run(self, seed: dict[str, Any]) -> Any:
        if self.schema is None:
            raise NotImplementedError(f"{self.__class__.__name__}.schema must be set.")
        return await self._llm.generate(system=self.system_prompt, user=f"Context: {seed}", schema=self.schema)