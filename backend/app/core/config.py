from enum import Enum
from typing import Optional
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class LLMProvider(str, Enum):
    """支持的 LLM 提供商"""
    OPENAI_COMPATIBLE = "openai-compatible"
    TENCENT_HUNYUAN = "tencent-hunyuan"
    LONGCAT = "longcat"


def detect_provider(base_url: str) -> LLMProvider:
    """根据 base_url 自动检测 LLM 提供商"""
    if not base_url:
        return LLMProvider.OPENAI_COMPATIBLE
    host = urlparse(base_url).hostname or ""
    if "longcat" in host:
        return LLMProvider.LONGCAT
    if "tencentmaas" in host or "tencent" in host:
        return LLMProvider.TENCENT_HUNYUAN
    return LLMProvider.OPENAI_COMPATIBLE


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "NovaMind API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── CORS ─────────────────────────────────────────────
    # Docker 部署时自动包含前端容器地址
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # ── Database ─────────────────────────────────────────
    # Docker Compose 时会被 environment 覆盖为 postgres:5432
    DATABASE_URL: str = "postgresql+asyncpg://postgres:novamind123@postgres:5432/novamind"

    # ── AI / LLM ─────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "gpt-3.5-turbo"
    # 可选，不设置则从 LLM_BASE_URL 自动检测
    LLM_PROVIDER: Optional[str] = None

    # ── Embedding ────────────────────────────────────────
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_MODEL: str = "doubao-embedding"
    EMBEDDING_DIMENSION: int = 1024

    # ── RAG ──────────────────────────────────────────────
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    RAG_TOP_K: int = 5

    # ── Tool: 百度地图（天气 + 经纬度） ──────────────────
    WEATHER_API_KEY: str = ""
    BAIDU_MAP_AK: str = ""

    # ── Memory ───────────────────────────────────────────
    MAX_MEMORY_MESSAGES: int = 20

    @property
    def provider(self) -> LLMProvider:
        if self.LLM_PROVIDER:
            return LLMProvider(self.LLM_PROVIDER)
        return detect_provider(self.LLM_BASE_URL)

    @property
    def supports_tool_calling(self) -> bool:
        return self.provider in (
            LLMProvider.OPENAI_COMPATIBLE,
            LLMProvider.LONGCAT,
            LLMProvider.TENCENT_HUNYUAN,
        )

    @property
    def supports_streaming(self) -> bool:
        return True


@lru_cache
def get_settings() -> Settings:
    return Settings()
