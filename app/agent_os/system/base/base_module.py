from typing import Any, Dict, Type
from pydantic import BaseModel

class BaseModule:
    def __init__(self, llm_factory: Any, model_type: str, system_prompt: str, schema: Type[BaseModel]):
        self._llm = llm_factory.get_model(model_type)
        self.system_prompt = system_prompt
        self.schema = schema

    async def run(self, seed: Dict[str, Any]) -> Any:
        return await self._llm.generate(
            system=self.system_prompt,
            user=f"Context: {seed}",
            schema=self.schema
        )