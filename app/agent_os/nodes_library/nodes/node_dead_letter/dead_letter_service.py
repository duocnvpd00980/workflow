class DeadLetterService:

    def __init__(self):

        self.failures = []

    async def push(
        self,
        data: dict,
    ):

        self.failures.append(data)