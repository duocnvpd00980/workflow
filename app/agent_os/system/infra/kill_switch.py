import asyncio

from agent_os.system.infra.logging_system import emit


class KillSwitch:

    def __init__(self):

        self._active = False

        self._lock = asyncio.Lock()

    def trip(self):

        self._active = True

        emit(
            "critical",
            event="kill_switch_tripped",
        )

    def reset(self):

        self._active = False

    @property
    def tripped(self):

        return self._active


KILL_SWITCH = KillSwitch()