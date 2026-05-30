# agent_os/system/watchdog.py
# ============================================================
# WATCHDOG — như WDT trong Arduino
# Chạy độc lập, không tin LangGraph, không tin state
# Đếm thời gian thực — trip nếu quá ngưỡng
# ============================================================
import asyncio
import time
from contextlib import asynccontextmanager

from .breach import Breach
from .law import Law, DEFAULT_LAW


class Watchdog:
    """
    Dùng như context manager:
        async with Watchdog(law) as wd:
            wd.tick()          # gọi mỗi node/iteration
            wd.error()         # gọi khi có lỗi
            await run_graph()
    """

    def __init__(self, law: Law = DEFAULT_LAW):
        self._law        = law
        self._t0         = time.monotonic()
        self._iterations = 0
        self._errors     = 0
        self._timer:     asyncio.Task | None = None

    # ── Public API ────────────────────────────────────────
    def tick(self) -> None:
        """Checkpoint đồng bộ — gọi mỗi lần node bắt đầu."""
        self._iterations += 1
        self._check()

    def error(self) -> None:
        """Ghi nhận lỗi — trip nếu vượt max."""
        self._errors += 1
        if self._errors >= self._law.max_errors:
            self._trip(f"error flood ({self._errors} errors)")

    def elapsed(self) -> float:
        return time.monotonic() - self._t0

    # ── Context manager ───────────────────────────────────
    async def __aenter__(self) -> "Watchdog":
        self._t0 = time.monotonic()
        self._timer = asyncio.create_task(self._hw_timer())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self._timer:
            self._timer.cancel()
            try:
                await self._timer
            except (asyncio.CancelledError, Breach):
                pass
        if isinstance(exc_val, Breach):
            return True  # nuốt — system đã xử lý
        return False

    # ── Internal ──────────────────────────────────────────
    def _check(self) -> None:
        if self.elapsed() >= self._law.max_seconds:
            self._trip(f"wall clock {self.elapsed():.1f}s >= {self._law.max_seconds}s")
        if self._iterations >= self._law.max_iterations:
            self._trip(f"iterations {self._iterations} >= {self._law.max_iterations}")

    def _trip(self, reason: str) -> None:
        raise Breach(reason)

    async def _hw_timer(self) -> None:
        """Hardware timer — trip wall clock ngay cả khi event loop bị block."""
        await asyncio.sleep(self._law.max_seconds)
        self._trip(f"hw timer: {self._law.max_seconds}s deadline exceeded")


# ── Entry point ───────────────────────────────────────────
@asynccontextmanager
async def run_guarded(law: Law = DEFAULT_LAW):
    """
    Mọi app chạy bên trong đây đều chịu luật system.

        async with run_guarded() as wd:
            wd.tick()
            result = await graph.ainvoke(input)
    """
    async with Watchdog(law) as wd:
        yield wd