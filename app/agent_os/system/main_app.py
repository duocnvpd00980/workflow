# agent_os/system/main_app.py

import logging
import traceback  # Thêm vào để debug chi tiết

from langchain_core.callbacks import AsyncCallbackHandler
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
        metadata = kwargs.get("metadata", {})
        if "langgraph_node" in metadata:
            self._wd.tick()

    async def on_chain_error(self, error, **kwargs) -> None:
        self._wd.error()

async def invoke(app, user_input: str, thread_id: str = "default") -> dict:
    try:
        async with run_guarded(LAW) as wd:
            result = await app.ainvoke(
                {"user_input": user_input},
                config={
                    "configurable": {"thread_id": thread_id},
                    "callbacks":    [_WatchdogCallback(wd)],
                    "recursion_limit": 20,
                },
            )
            return {"ok": True, "result": result}

    except Breach as b:
        log.critical("SYSTEM TRIP (Breach): %s", b.reason)
        return {"ok": False, "error": f"Breach: {b.reason}", "reason": b.reason}
        
    except Exception as e:
        # Bắt mọi lỗi khác (GraphRecursionError, ValidationError, v.v.)
        err_msg = str(e)
        log.error("SYSTEM CRASH: %s\n%s", err_msg, traceback.format_exc())
        return {"ok": False, "error": f"Exception: {err_msg}"}