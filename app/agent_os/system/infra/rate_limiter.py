import asyncio
import time

from agent_os.system.infra.app_config import CFG


class RateLimiter:

    def __init__(self):

        self._rpm = CFG.rate_limit_per_min

        self._buckets = {}

        self._lock = asyncio.Lock()

    async def check(
        self,
        session_id: str,
    ) -> bool:

        now = time.monotonic()

        async with self._lock:

            bucket = self._buckets.setdefault(
                session_id,
                []
            )

            self._buckets[session_id] = [
                t for t in bucket
                if now - t < 60
            ]

            if len(self._buckets[session_id]) >= self._rpm:

                return False

            self._buckets[session_id].append(now)

            return True


RATE_LIMITER = RateLimiter()