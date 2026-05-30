# agent_os/workflows/app_state.py
import asyncio
from agent_os.workflows.mainboard import factory, board

_main_app = None
_lock = asyncio.Lock()

async def get_main_app():
    global _main_app
    if _main_app is None:
        async with _lock:
            if _main_app is None:  # double-check
                db_checkpointer = await factory.get_checkpointer().__aenter__()
                _main_app = board.compile(checkpointer=db_checkpointer)
    return _main_app