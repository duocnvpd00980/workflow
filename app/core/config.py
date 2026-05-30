from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_api_key: str
    database_url: str = "sqlite+aiosqlite:///./chat.db"
    gemini_model: str = "gemini-2.0-flash"

@lru_cache
def get_settings() -> Settings:
    return Settings()
