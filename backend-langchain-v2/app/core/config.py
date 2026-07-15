import os
from enum import Enum
from typing import Optional, List
from urllib.parse import urlparse
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    """系统全局配置类，基于 pydantic-settings 规范加载环境变量"""
    model_config = SettingsConfigDict(
        # 允许从当前目录或父级目录查找 .env 文件，以适应不同的启动入口
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "NovaMind LangChain v2 API"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = False

    # ── CORS ─────────────────────────────────────────────
    # Docker 部署或本地调试跨域限制
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                return [x.strip() for x in v.split(",") if x.strip()]
        return v

    # ── Database ─────────────────────────────────────────
    # 我们在新架构中将继续采用 PostgreSQL 存放数据与向量
    # 这里我们定义 DATABASE_URL
    POSTGRES_HOST: str = "59.110.139.156"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "novamind123"
    POSTGRES_DB: str = "novamind"
    POSTGRES_PORT: int = 5432

    # 异步连接 URL (SQLAlchemy 配合 asyncpg 使用)
    DATABASE_URL: Optional[str] = None

    # 同步连接 URL (适用于 psycopg 驱动直连，符合 LangGraph / pgvector 部分官方库的偏好)
    DATABASE_URL_SYNC: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v, info):
        if v:
            return v
        data = info.data
        user = data.get("POSTGRES_USER")
        password = data.get("POSTGRES_PASSWORD")
        host = data.get("POSTGRES_HOST")
        port = data.get("POSTGRES_PORT")
        db = data.get("POSTGRES_DB")
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

    @field_validator("DATABASE_URL_SYNC", mode="before")
    @classmethod
    def assemble_db_url_sync(cls, v, info):
        if v:
            return v
        data = info.data
        user = data.get("POSTGRES_USER")
        password = data.get("POSTGRES_PASSWORD")
        host = data.get("POSTGRES_HOST")
        port = data.get("POSTGRES_PORT")
        db = data.get("POSTGRES_DB")
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    # ── AI / LLM ─────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "gpt-3.5-turbo"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
