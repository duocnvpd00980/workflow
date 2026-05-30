# agent_os/system/streaming.py
"""
Streaming entry point duy nhất cho mọi caller cần stream SSE.
Tích hợp Law + Watchdog + Breach.

Yields (event_type, value):
  ("node",      node_key)        ← mỗi node chạy xong
  ("interrupt", payload_json)    ← graph dừng tại interrupt
  ("error",     reason)          ← pipeline error / breach / timeout
  ("done",      None)            ← luôn yield cuối cùng, dù crash hay không
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from langchain_core.callbacks import AsyncCallbackHandler
from langgraph.errors import GraphInterrupt

from agent_os.system.breach import Breach
from agent_os.system.law import Law
from agent_os.system.watchdog import run_guarded

log = logging.getLogger("agent_os")

LAW = Law(
    max_seconds    = 30.0,
    max_iterations = 50,
    max_rework     = 3,
    max_errors     = 10,
)


class _WatchdogCallback(AsyncCallbackHandler):
    def __init__(self, wd):
        self._wd = wd

    async def on_chain_start(self, serialized, inputs, **kwargs) -> None:
        if "langgraph_node" in kwargs.get("metadata", {}):
            self._wd.tick()

    async def on_chain_error(self, error, **kwargs) -> None:
        self._wd.error()


async def stream_guarded(
    app,
    graph_input,
    thread_id: str,
) -> AsyncGenerator[tuple[str, str | None], None]:
    """
    Async generator — LUÔN kết thúc bằng ("done", None).
    Caller không cần try/except, không cần tự yield done.
    """
    pipeline_error: str | None = None

    try:
        async with run_guarded(LAW) as wd:
            config = {
                "configurable":    {"thread_id": thread_id},
                "callbacks":       [_WatchdogCallback(wd)],
                "recursion_limit": 20,
            }

            async with asyncio.timeout(LAW.max_seconds):
                async for chunk in app.astream(graph_input, config=config):

                    # ── Interrupt ─────────────────────────────────────────
                    if "__interrupt__" in chunk:
                        payload = chunk["__interrupt__"][0].value
                        yield ("interrupt", json.dumps(payload, ensure_ascii=False))
                        return  # done yield ở finally

                    # ── Node hoàn thành ───────────────────────────────────
                    for node_key in chunk:
                        if not node_key.startswith("__"):
                            yield ("node", node_key)

    except asyncio.TimeoutError:
        log.error("[stream_guarded] timeout thread=%s", thread_id)
        pipeline_error = "timeout"

    except Breach as b:
        log.critical("[stream_guarded] Breach: %s thread=%s", b.reason, thread_id)
        pipeline_error = f"Breach: {b.reason}"

    except Exception as e:
        log.error("[stream_guarded] CRASH (%s): %s thread=%s", type(e).__name__, e, thread_id)
        pipeline_error = repr(e)

    finally:
        if pipeline_error:
            yield ("error", pipeline_error)
        yield ("done", None)