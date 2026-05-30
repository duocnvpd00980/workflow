# app/core/runtime.py
from __future__ import annotations
from typing import Any
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from pydantic import BaseModel
from app.core.config import get_settings

_S = get_settings()
_OLLAMA = _S.ollama_base_url


class LLMEngine:
    def __init__(self, model: str, base_url: str | None = None) -> None:
        self.model, self.base_url = model, base_url

    def lc(self) -> BaseChatModel:
        return (ChatOllama(model=self.model, base_url=self.base_url) if self.base_url
                else ChatGoogleGenerativeAI(model=self.model, google_api_key=_S.google_api_key))


class EmbedEngine:
    def __init__(self, model: str, base_url: str | None = None) -> None:
        self.model, self.base_url = model, base_url


class ModelRegistry:
    def __init__(self, llm: dict[str, LLMEngine], embed: dict[str, EmbedEngine]) -> None:
        self._llm, self._embed = llm, embed

    def _get(self, d: dict, key: str, fallback: str):
        return d.get(key) or d.get(fallback) or next(iter(d.values()))

    def llm(self, key="default")        -> LLMEngine:   return self._get(self._llm,   key, "default")
    def embed(self, key="default_embed")-> EmbedEngine:  return self._get(self._embed, key, "default_embed")
    def lc(self, key="default")         -> BaseChatModel: return self.llm(key).lc()


def build_runtime() -> dict[str, Any]:
    E = lambda m, b=None: LLMEngine(m, b)
    if _S.is_dev:
        llms = {"default": E("qwen3:0.6b",  _OLLAMA), "fast":   E("qwen2.5:3b",  _OLLAMA),
                "large":   E("llama3.1:8b", _OLLAMA), "router": E("qwen2.5:7b",  _OLLAMA)}
    else:
        llms = {"default": E("gemini-2.0-flash"), "fast":   E("gemini-2.0-flash"),
                "large":   E("gemini-1.5-pro"),   "router": E("gemini-2.0-flash")}

    return {"registry": ModelRegistry(llms, {"default_embed": EmbedEngine("nomic-embed-text:latest", _OLLAMA)})}


class Module:
    def __init__(self, registry: ModelRegistry, model="default",
                 system_prompt="", schema: type[BaseModel] | None = None) -> None:
        self._llm, self.system_prompt, self.schema = registry.llm(model), system_prompt, schema

    async def run(self, seed: dict[str, Any]) -> Any:
        if self.schema is None:
            raise NotImplementedError(f"{self.__class__.__name__}.schema must be set.")
        return await self._llm.lc().ainvoke(f"Context: {seed}")