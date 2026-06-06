from pydantic_settings import BaseSettings
from pydantic import ConfigDict  # 1. Import thêm ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(extra="ignore", env_file=".env") 

    GROQ_API_KEY: str = "YOUR_GROQ_API_KEY"
    GROQ_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    DATABASE_URL: str = "sqlite:///./workflow.db"
    

settings = Settings()