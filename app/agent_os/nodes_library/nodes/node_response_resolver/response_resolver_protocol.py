# =========================================================
# FILE: response_resolver_protocol.py
# =========================================================
from pydantic import BaseModel, ConfigDict


class ResponseResolverOutput(BaseModel):
    """
    RESPONSE RESOLVER PROTOCOL
    Hợp đồng dữ liệu đầu ra của Bộ phân tích phản hồi và định tuyến luồng.
    """

    route: str
    reasoning: str
    confidence_score: float
    next_steps: list[str]

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
    )
