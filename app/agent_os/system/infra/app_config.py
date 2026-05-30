from pydantic import BaseModel, ConfigDict

# =============================================================================
# GLOBAL APP CONFIG
# =============================================================================

class AppConfig(BaseModel):

    model_config = ConfigDict(frozen=True)

    # LLM
    default_model: str = "llama3.2:3b"

    # Runtime
    max_retries: int = 3
    node_timeout: float = 60.0
    sla_timeout: float = 300.0

    # Budget
    cost_per_1k_tokens: float = 0.0009

    # Limits
    max_input_len: int = 4000
    max_outputs_kept: int = 5

    # Blog Pipeline
    max_blog_revisions: int = 3


CFG = AppConfig()