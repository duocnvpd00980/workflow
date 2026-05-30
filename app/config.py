# app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    is_dev: bool = True

    # DB
    database_url: str = "sqlite+aiosqlite:///./app.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()