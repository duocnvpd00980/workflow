from pydantic import BaseModel


class ValidatorVerdict(BaseModel):

    passed: bool = False

    score: float = 0.0

    issues: str = ""

    needs_retry: bool = False

    retry_reason: str = ""