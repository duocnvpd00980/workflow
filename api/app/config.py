from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Cấu hình tự động nạp từ file .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Môi Trường & Hệ Thống ──────────────────────────────────
    is_dev: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./chat.db"

    # ── Cấu Hình Gemini ──────────────────────────────────────
    GEMINI_API_KEY: str  # Không gán mặc định để bắt buộc phải khai báo trong .env
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"

    # ── Cấu Hình Groq ────────────────────────────────────────
    GROQ_API_KEY: str    # Bắt buộc khai báo trong .env để bảo mật
    GROQ_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    GROQ_MODEL_GPT: str = "openai/gpt-oss-120b"

    # ── Cấu Hình Bên Thứ Ba Khác ──────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    POLLINATIONS_API_KEY: str = ""  # Để mặc định chuỗi rỗng
    JINA_API_KEY: str = ""          # Để mặc định chuỗi rỗng


@lru_cache
def get_settings() -> Settings:
    return Settings()