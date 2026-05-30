# agent_os/system/main.py
"""
System runtime — đóng gói toàn bộ pipeline primitives.
Nơi khác chỉ import từ đây, không tự build config / watchdog / error handling.

Export:
  LAW, InvokeResult
  invoke(app, user_input, thread_id)           → InvokeResult
  resume(app, thread_id, action, feedback)     → InvokeResult
  stream_events(app, graph_input, thread_id)   → AsyncIterator[(node_key, error|None)]
  _safe_get_snapshot(app, thread_id)           → snapshot | None
  _is_interrupted_at_human_review(snapshot)    → bool
  _extract_draft(snapshot)                     → str
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from langchain_core.callbacks import AsyncCallbackHandler
from langgraph.types import Command

from agent_os.system.breach import Breach
from agent_os.system.law import Law
from agent_os.system.watchdog import run_guarded

log = logging.getLogger("agent_os")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

LAW = Law(
    max_seconds    = 30.0,
    max_iterations = 50,
    max_rework     = 3,
    max_errors     = 10,
)

RECURSION_LIMIT = 20

# ─────────────────────────────────────────────────────────────────────────────
# InvokeResult
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class InvokeResult:
    ok:      bool
    result:  dict[str, Any] = field(default_factory=dict)
    waiting: bool           = False   # True → dừng tại node_human_review
    draft:   str            = ""      # Nội dung chờ review
    error:   str            = ""
    reason:  str            = ""      # Breach reason

# ─────────────────────────────────────────────────────────────────────────────
# Watchdog callback (internal)
# ─────────────────────────────────────────────────────────────────────────────

class _WatchdogCallback(AsyncCallbackHandler):
    def __init__(self, wd):
        self._wd = wd

    async def on_chain_start(self, serialized, inputs, **kwargs) -> None:
        if "langgraph_node" in kwargs.get("metadata", {}):
            self._wd.tick()

    async def on_chain_error(self, error, **kwargs) -> None:
        self._wd.error()

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_config(thread_id: str, wd) -> dict:
    return {
        "configurable":    {"thread_id": thread_id},
        "callbacks":       [_WatchdogCallback(wd)],
        "recursion_limit": RECURSION_LIMIT,
    }

# ─────────────────────────────────────────────────────────────────────────────
# Exported helpers — caller dùng để xử lý snapshot
# ─────────────────────────────────────────────────────────────────────────────

async def _safe_get_snapshot(app, thread_id: str):
    try:
        return await app.aget_state({"configurable": {"thread_id": thread_id}})
    except Exception as exc:
        log.error("[main] aget_state failed thread=%s: %s", thread_id, exc)
        return None


def _is_interrupted_at_human_review(snapshot) -> bool:
    if snapshot is None:
        return False
    return "node_human_review" in list(getattr(snapshot, "next", []) or [])


def _extract_draft(snapshot) -> str:
    if snapshot is None:
        return ""
    for task in getattr(snapshot, "tasks", []) or []:
        for intr in getattr(task, "interrupts", []) or []:
            v = getattr(intr, "value", {})
            if isinstance(v, dict) and "draft" in v:
                return v["draft"]
    for intr in getattr(snapshot, "interrupts", []) or []:
        v = getattr(intr, "value", {})
        if isinstance(v, dict) and "draft" in v:
            return v["draft"]
    return ""

# ─────────────────────────────────────────────────────────────────────────────
# stream_events — bao gồm watchdog + timeout + error handling
# Caller chỉ cần iterate, không tự handle Breach / timeout / watchdog
# ─────────────────────────────────────────────────────────────────────────────

async def stream_events(
    app,
    graph_input,        # dict (initial) | Command(resume=...) (resume)
    thread_id: str,
) -> AsyncIterator[tuple[str, Exception | None]]:
    """
    Yields (node_key, None)        — mỗi node hoàn thành
    Yields ("",       exception)   — nếu có lỗi (cuối cùng)
    """
    pipeline_error: Exception | None = None

    try:
        async with run_guarded(LAW) as wd:
            config = _build_config(thread_id, wd)
            async with asyncio.timeout(LAW.max_seconds):
                async for event in app.astream(graph_input, config, stream_mode="updates"):
                    for node_key in event:
                        yield node_key, None

    except Breach as b:
        log.critical("[stream_events] Breach: %s thread=%s", b.reason, thread_id)
        pipeline_error = RuntimeError(f"Breach: {b.reason}")

    except TimeoutError:
        log.error("[stream_events] timeout thread=%s", thread_id)
        pipeline_error = TimeoutError("graph timeout")

    except Exception as exc:
        log.warning("[stream_events] error (%s): %s thread=%s", type(exc).__name__, exc, thread_id)
        pipeline_error = exc

    if pipeline_error:
        yield "", pipeline_error

# ─────────────────────────────────────────────────────────────────────────────
# invoke — ainvoke wrapper, bao gồm human_review interrupt check
# ─────────────────────────────────────────────────────────────────────────────

async def invoke(
    app,
    user_input: str,
    thread_id: str = "default",
) -> InvokeResult:
    try:
        async with run_guarded(LAW) as wd:
            result = await app.ainvoke(
                {"user_input": user_input},
                config=_build_config(thread_id, wd),
            )
            snapshot = await _safe_get_snapshot(app, thread_id)

            if _is_interrupted_at_human_review(snapshot):
                draft = _extract_draft(snapshot)
                log.info("[invoke] paused human_review thread=%s draft_len=%d", thread_id, len(draft))
                return InvokeResult(ok=True, result=result or {}, waiting=True, draft=draft)

            return InvokeResult(ok=True, result=result or {})

    except Breach as b:
        log.critical("[invoke] Breach: %s", b.reason)
        return InvokeResult(ok=False, error=f"Breach: {b.reason}", reason=b.reason)

    except Exception as e:
        log.error("[invoke] CRASH: %s\n%s", e, traceback.format_exc())
        return InvokeResult(ok=False, error=f"Exception: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# resume — Command(resume=...) wrapper
# ─────────────────────────────────────────────────────────────────────────────

async def resume(
    app,
    thread_id: str,
    action: str,
    feedback: str = "",
) -> InvokeResult:
    try:
        async with run_guarded(LAW) as wd:
            result = await app.ainvoke(
                Command(resume={"action": action.strip().lower(), "feedback": feedback.strip()}),
                config=_build_config(thread_id, wd),
            )
            snapshot = await _safe_get_snapshot(app, thread_id)

            if _is_interrupted_at_human_review(snapshot):
                draft = _extract_draft(snapshot)
                log.info("[resume] paused again human_review thread=%s", thread_id)
                return InvokeResult(ok=True, result=result or {}, waiting=True, draft=draft)

            return InvokeResult(ok=True, result=result or {})

    except Breach as b:
        log.critical("[resume] Breach: %s", b.reason)
        return InvokeResult(ok=False, error=f"Breach: {b.reason}", reason=b.reason)

    except Exception as e:
        log.error("[resume] CRASH: %s\n%s", e, traceback.format_exc())
        return InvokeResult(ok=False, error=f"Exception: {e}")