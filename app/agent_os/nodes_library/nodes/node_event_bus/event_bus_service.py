class EventBusService:

    def __init__(self):

        self.subscribers = {}

    async def publish(
        self,
        event_name: str,
        data,
    ):

        print(
            f"[EVENT] {event_name}"
        )

    async def subscribe(
        self,
        event_name: str,
        handler,
    ):

        self.subscribers[
            event_name
        ] = handler