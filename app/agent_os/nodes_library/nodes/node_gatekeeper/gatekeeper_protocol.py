from pydantic import BaseModel
from typing import List, Optional


class GatekeeperOutput(BaseModel):
    gatekeeper_passed: bool = True
    headline: str = ""
    content: str = ""
    brand_color: str = "#000000"
    risk_score: float = 0.0

    violations: List[str] = []
    reason: str = "OK"
    reason_detail: Optional[str] = None

    @property
    def is_safe(self) -> bool:
        return self.gatekeeper_passed
