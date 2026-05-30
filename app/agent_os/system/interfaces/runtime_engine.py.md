# =============================================================================
# RUNTIME ENGINE (LLM ABSTRACTION LAYER - INDUSTRIAL STANDARD)
# LiteLLM + Instructor + Pydantic v2
# =============================================================================

from typing import Protocol, Type, TypeVar, Any
from pydantic import BaseModel
import instructor
import litellm

T = TypeVar("T", bound=BaseModel)


# -----------------------------------------------------------------------------
# INTERFACE
# -----------------------------------------------------------------------------

class LLMEngine(Protocol):
    async def generate(
        self,
        *,
        system: str,
        user: str,
        schema: Type[T],
        temperature: float = 0.3,
    ) -> T:
        ...


# -----------------------------------------------------------------------------
# LITELLM + INSTRUCTOR ADAPTER
# -----------------------------------------------------------------------------

class LiteLLMEngine:
    def __init__(self, model: str, base_url: str | None = None):
        self.model = model
        self.base_url = base_url
        self.client = instructor.patch(create=litellm.acompletion)

    async def generate(
        self,
        *,
        system: str,
        user: str,
        schema: Type[T],
        temperature: float = 0.1,
    ) -> T:
        return await self.client(
            model=self.model,
            temperature=temperature,
            response_model=schema,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            api_base=self.base_url, 
        )


# -----------------------------------------------------------------------------
# FACTORY (plug anything here)
# -----------------------------------------------------------------------------

def build_runtime() -> dict:
    """
    Dependency injection container
    """

    return {
        "llm_engine": LiteLLMEngine(
            model="ollama/qwen2.5:1.5b",
            base_url="http://192.168.101.18:11434"
        )
    }