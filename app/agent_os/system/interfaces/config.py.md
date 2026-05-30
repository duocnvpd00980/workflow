from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class NodeConfig:
    services: dict
    session_id: Optional[str] = None
    budget_limit: float = 2.0