import asyncio
import random

class CircuitGuard:

    def __init__(self, cfg):
        self.cfg = cfg

    async def retry(self, fn, max_retries: int):

        last_error = None

        for i in range(max_retries):

            try:
                return await fn()

            except Exception as e:

                last_error = str(e)

                wait = self.cfg.base_backoff * (2 ** i)
                wait += random.uniform(0, 0.3)

                await asyncio.sleep(wait)

        raise RuntimeError(last_error)