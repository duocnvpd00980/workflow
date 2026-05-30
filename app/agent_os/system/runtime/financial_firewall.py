from agent_os.system.infra.budget_guard import (
    BUDGET_GUARD,
)

from agent_os.system.infra.circuit_breaker import (
    CIRCUIT_BREAKER,
)


class FinancialFirewall:

    async def protect(
        self,
        *,
        node: str,
        text: str,
        current_cost: float,
        limit: float,
    ):

        estimated = BUDGET_GUARD.estimate_cost(
            text
        )

        BUDGET_GUARD.enforce(
            current=current_cost,
            estimated=estimated,
            limit=limit,
            node=node,
        )

        CIRCUIT_BREAKER.assert_closed()


FIREWALL = FinancialFirewall()