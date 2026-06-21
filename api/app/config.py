from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Cấu hình tự động lấy từ file .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Chỉ định nghĩa 1 lần duy nhất cho mỗi biến
    # Các giá trị ở đây là "Default values" nếu không tìm thấy trong .env
    GEMINI_API_KEY: str = "AIzaSyBrx7ay5v0GC08fq0qxS_zHyuuKqaI-Jg0"
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    is_dev: bool = True
    # Dùng chuẩn aiosqlite cho database
    DATABASE_URL: str = "sqlite+aiosqlite:///./chat.db"
    
    # Bảo mật: Không nên để key thật ở đây, chỉ để chuỗi rỗng
    GROQ_API_KEY: str = "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"
    GROQ_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"

    POLLINATIONS_API_KEY: str = "sk_J68kYhDowZ8FTDPupSlolhNEcnqsWZ1P"

    JINA_API_KEY : str = "jina_3de0aae4312d41f382883d98441b1cb8LecWrx2z5tNNFGYJuWIxPWqMXeo9"

@lru_cache
def get_settings() -> Settings:
    return Settings()