from __future__ import annotations

import uuid

from datetime import datetime

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Generic,
    TypeVar,
    Literal,
)

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
)

# =========================================================
# GENERIC
# =========================================================

T = TypeVar("T")

# =========================================================
# TELEMETRY
# =========================================================

class Telemetry(BaseModel):

    latency_ms: float = 0.0

    input_tokens: int = 0

    output_tokens: int = 0

    total_tokens: int = 0

    cost_usd: float = 0.0

# =========================================================
# BODY FRAME
# =========================================================

class BodyFrame(BaseModel):

    model_config = ConfigDict(
        extra="forbid"
    )

    status: Literal[
        "SUCCESS",
        "FAILED",
        "EMPTY",
    ]

    text: str = ""

    records: List[Any] = Field(
        default_factory=list
    )

    entities: List[Any] = Field(
        default_factory=list
    )

    state: Dict[str, Any] = Field(
        default_factory=dict
    )

    metrics: Dict[str, Any] = Field(
        default_factory=dict
    )

    context: Dict[str, Any] = Field(
        default_factory=dict
    )

    route: Optional[str] = None

    error: Optional[str] = None


# =========================================================
# STANDARD FRAME
# =========================================================

class StandardFrame(
    BaseModel,
    Generic[T],
):

    model_config = ConfigDict(
        extra="forbid"
    )

    execution_id: str = Field(
        default_factory=lambda:
        str(uuid.uuid4())
    )

    trace_id: str = Field(
        default_factory=lambda:
        str(uuid.uuid4())
    )

    parent_trace_id: Optional[str] = None

    node_id: str

    payload: T

    timestamp: float = Field(
        default_factory=lambda:
        datetime.now().timestamp()
    )

    telemetry: Telemetry = Field(
        default_factory=Telemetry
    )

    @classmethod
    def emit(
        cls,
        registry_key: str,
        payload: T,
        telemetry: dict | None = None,
        trace_id: str | None = None,
        parent_trace_id: str | None = None,
    ) -> dict:

        frame = cls(

            node_id=registry_key,

            payload=payload,

            telemetry=Telemetry(
                **telemetry
            ) if telemetry else Telemetry(),

            trace_id=
            trace_id or str(uuid.uuid4()),

            parent_trace_id=
            parent_trace_id,
        )

        return {
            registry_key:
            frame.model_dump(

                mode="json",

                exclude_none=True,

                exclude_defaults=True,
            )
        }

# =========================================================
# TYPE ALIAS
# =========================================================

type BusFrame = (
    StandardFrame[BodyFrame]
    | None
)