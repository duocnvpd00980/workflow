from pydantic import BaseModel
from typing import Any, Optional


class CacheMemoryOutput(BaseModel):
    cache_key: str
    cache_hit: bool = False
    cached_data: Optional[Any] = None
