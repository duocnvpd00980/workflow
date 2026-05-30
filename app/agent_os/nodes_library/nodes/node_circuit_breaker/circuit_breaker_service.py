class CircuitBreakerService:

    def __init__(self):

        self.failures = {}

        self.threshold = 5

    async def register_failure(
        self,
        node_name: str,
    ):

        count = self.failures.get(
            node_name,
            0,
        )

        count += 1

        self.failures[node_name] = count

        return {

            "is_open": count >= self.threshold,

            "failure_count": count,

            "threshold": self.threshold,

            "blocked_node": (

                node_name

                if count >= self.threshold

                else None
            )
        }