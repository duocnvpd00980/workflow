from agent_os.system.infra.app_config import CFG

from agent_os.system.shields.shield_faults import (
    FuseBlownException,
)


class BudgetGuard:

    def estimate_cost(
        self,
        text: str,
    ) -> float:

        tokens = max(1, len(text) // 3)

        return (
            (tokens / 1000)
            * CFG.cost_per_1k_tokens
        )

    def enforce(
        self,
        *,
        current: float,
        estimated: float,
        limit: float,
        node: str,
    ):

        if current + estimated > limit:

            raise FuseBlownException(
                f"{node}: budget exceeded"
            )


BUDGET_GUARD = BudgetGuard()