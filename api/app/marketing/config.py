from pydantic_settings import BaseSettings
from pydantic import ConfigDict  # 1. Import thêm ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(extra="ignore", env_file=".env") 

    GROQ_API_KEY: str = "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"
    GROQ_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    DATABASE_URL: str = "sqlite:///./workflow.db"
    

settings = Settings()