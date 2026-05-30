from agent_os.system.runtime.llm_router import LLM_ROUTER


class ServiceContainer:

    def __init__(self, llm_engine):

        self.llm_engine = llm_engine

        self.router = LLM_ROUTER