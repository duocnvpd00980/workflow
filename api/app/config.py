from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
  
@lru_cache
def get_settings() -> Settings:
    return Settings()