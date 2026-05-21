from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "NovaMind API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── CORS ─────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/novamind"

    # ── AI / LLM ─────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "longcat"

    # ── Embedding ────────────────────────────────────────
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_MODEL: str = "doubao-embedding"
    EMBEDDING_DIMENSION: int = 1024

    # ── RAG ──────────────────────────────────────────────
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    RAG_TOP_K: int = 5

    # ── Tool: Weather ────────────────────────────────────
    WEATHER_API_KEY: str = ""

    # ── Memory ───────────────────────────────────────────
    MAX_MEMORY_MESSAGES: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()

# Trigger final reload with verified settings
