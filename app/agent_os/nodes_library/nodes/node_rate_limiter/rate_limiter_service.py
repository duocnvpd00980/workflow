import time


class RateLimiterService:
    def __init__(self):

        self.storage = {}

        self.window_seconds = 60

        self.limit_per_minute = 30

    async def check_limit(
        self,
        user_key: str,
    ) -> dict:

        now = time.time()

        if user_key not in self.storage:
            self.storage[user_key] = []

        requests = self.storage[user_key]

        requests = [ts for ts in requests if now - ts < self.window_seconds]

        requests.append(now)

        self.storage[user_key] = requests

        allowed = len(requests) <= self.limit_per_minute

        return {
            "allowed": allowed,
            "current_requests": len(requests),
            "limit_per_minute": self.limit_per_minute,
            "blocked_reason": (None if allowed else "RATE_LIMIT_EXCEEDED"),
        }
