class CacheMemoryService:

    def __init__(self):

        self._memory = {}

    async def get(
        self,
        key: str,
    ):

        return self._memory.get(key)

    async def set(
        self,
        key: str,
        value,
    ):

        self._memory[key] = value