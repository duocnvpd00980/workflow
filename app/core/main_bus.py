# agent_os/bus/main_bus.py
from __future__ import annotations

from operator import add
from typing import Annotated, Union

from pydantic import BaseModel, ConfigDict, Field

from .protocol import BodyFrame, StandardFrame

from langchain_core.messages import BaseMessage

from langgraph.graph.message import add_messages

BusFrame = Union[StandardFrame[BodyFrame], None]


def _merge(left: BusFrame, right: BusFrame) -> BusFrame:
    """Giữ frame cũ nếu frame mới None — an toàn khi fan-out song song."""
    return left if right is None else right


class MainBus(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # ── Input ─────────────────────────────────────────────────────────────────
    user_input: str = ""
    language: str = "vi"
    budget_limit: float = 2.0
    chat_history: list[dict] = Field(default_factory=list)

    # ── Context — truyền từ Django xuống graph ────────────────────────────────
    conversation_id: str = ""
    msg_id: str = ""

    # ── Registers ─────────────────────────────────────────────────────────────
    input_guard: BusFrame = None
    supervisor: BusFrame = None
    marketing: Annotated[BusFrame, _merge] = None
    knowledge: Annotated[BusFrame, _merge] = None
    aggregator: BusFrame = None
    result_store: BusFrame = None
    fallback_search: BusFrame = None
    cache_layer: Annotated[BusFrame, _merge] = None
    lightweight_chat: Annotated[BusFrame, _merge] = None
    human_review: Annotated[BusFrame, _merge] = None
    shared_state: Annotated[BusFrame, _merge] = None
    output_guard: Annotated[BusFrame, _merge] = None
    generation: Annotated[BusFrame, _merge] = None
    evaluator: Annotated[BusFrame, _merge] = None
    final_response: Annotated[BusFrame, _merge] = None
    cache_read: Annotated[BusFrame, _merge] = None
    cache_write: Annotated[BusFrame, _merge] = None
    heuristic_router: BusFrame = None
    knowledge_base: BusFrame = None
    relevance_check: BusFrame = None
    llm_generation: BusFrame = None

    # ── Counters ──────────────────────────────────────────────────────────────
    steps: int = 0
    max_steps: int = 10
    rework_count: int = 0
    max_rework: int = 2
    is_aborted: bool = False
    errors: Annotated[list[str], add] = Field(default_factory=list)

    # ── Cầu chì ──────────────────────────────────────────────────────────────
    def is_blown(self) -> bool:
        return (
            self.is_aborted
            or self.steps >= self.max_steps
            or self.rework_count > self.max_rework
        )

    # ── Routing — pure read, không side-effect ────────────────────────────────
    def route(self, slot: str, default: str = "end") -> str:
        if self.is_blown():
            return "end"

        frame = getattr(self, slot, None)

        if frame is None or getattr(frame, "payload", None) is None:
            return default

        return getattr(frame.payload, "route", None) or default
