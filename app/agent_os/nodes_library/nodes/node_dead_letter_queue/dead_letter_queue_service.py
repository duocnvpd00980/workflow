class DeadLetterQueueService:
    def __init__(self):

        self.queue = []

    async def push(
        self,
        payload: dict,
    ):

        self.queue.append(payload)

        return True
