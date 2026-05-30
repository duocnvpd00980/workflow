from __future__ import annotations
from typing import Any, Callable
from langgraph.errors import GraphInterrupt
from langgraph.types import RetryPolicy
from agent_os.system.shields.run_shielded import shielded


def _abort(node_id: str, reason: str) -> dict:
    return {
        "is_aborted": True,
        "errors": [f"[{node_id}] {reason}"],
    }


class Node:

    def __init__(self, key: str, fn: Callable):
        self.id = key
        self.fn = fn
        self.policy: RetryPolicy | None = None
        self.is_shielded = False

    def shield(self) -> Node:
        self.is_shielded = True
        return self

    def retry(self, policy: RetryPolicy) -> Node:
        self.policy = policy
        return self

    def mount(self, board: Any) -> str:
        node_id = self.id
        logic = shielded(node_name=node_id, fn=self.fn) if self.is_shielded else self.fn

        async def wrapper(state: Any, *args, **kwargs) -> dict:
            if state.is_blown():
                return _abort(node_id, f"fuse blown (aborted={state.is_aborted})")
            try:
                result = await logic(state, *args, **kwargs)
                return result if isinstance(result, dict) else {}
            except GraphInterrupt:
                raise  # ← LangGraph dùng exception này để dừng graph, không được bắt
            except Exception as e:
                return _abort(node_id, f"exception: {e!r}")

        board.add_node(node_id, wrapper, retry_policy=self.policy)
        return node_id