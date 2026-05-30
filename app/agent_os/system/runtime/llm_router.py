from agent_os.system.infra.app_config import CFG


class LLMRouter:

    def model_for(self, agent_id: str) -> str:

        mapping = {
            "AGENT_ADS": "llama3.2:3b",
            "AGENT_EMAIL": "llama3.2:3b",
        }

        return mapping.get(
            agent_id,
            CFG.default_model
        )


LLM_ROUTER = LLMRouter()