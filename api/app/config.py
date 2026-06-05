from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Cấu hình tự động lấy từ file .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Chỉ định nghĩa 1 lần duy nhất cho mỗi biến
    # Các giá trị ở đây là "Default values" nếu không tìm thấy trong .env
    GOOGLE_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    is_dev: bool = True
    # Dùng chuẩn aiosqlite cho database
    DATABASE_URL: str = "sqlite+aiosqlite:///./chat.db"
    
    # Bảo mật: Không nên để key thật ở đây, chỉ để chuỗi rỗng
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"

@lru_cache
def get_settings() -> Settings:
    return Settings()