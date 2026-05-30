import asyncio
import time

from enum import Enum

from agent_os.system.infra.app_config import CFG

from agent_os.system.infra.logging_system import emit

from agent_os.system.shields.shield_faults import (
    CircuitOpenException,
)


class CircuitState(str, Enum):

    CLOSED = "closed"

    OPEN = "open"

    HALF_OPEN = "half_open"


class CircuitBreaker:

    def __init__(self):

        self._state = CircuitState.CLOSED

        self._failures = 0

        self._opened_at = 0.0

        self._lock = asyncio.Lock()

    @property
    def state(self):

        if (
            self._state == CircuitState.OPEN
            and
            time.monotonic() - self._opened_at
            >= CFG.cb_recovery_seconds
        ):
            self._state = CircuitState.HALF_OPEN

        return self._state

    def assert_closed(self):

        if self.state == CircuitState.OPEN:

            raise CircuitOpenException(
                "Circuit breaker OPEN"
            )

    async def record_success(self):

        async with self._lock:

            self._failures = 0

            self._state = CircuitState.CLOSED

    async def record_failure(self):

        async with self._lock:

            self._failures += 1

            if self._failures >= CFG.cb_failure_threshold:

                self._state = CircuitState.OPEN

                self._opened_at = time.monotonic()

                emit(
                    "warning",
                    event="circuit_open",
                    failures=self._failures,
                )


CIRCUIT_BREAKER = CircuitBreaker()