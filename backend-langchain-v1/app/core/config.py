from pydantic_settings import BaseSettings
from pydantic import ConfigDict, model_validator
from typing import List, Optional, Self

class Settings(BaseSettings):
    APP_NAME: str = "NovaMind-LangChain"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库连接
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "novamind123"
    POSTGRES_DB: str = "novamind"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None
    
    # 字节火山引擎 Embedding 配置
    EMBEDDING_API_KEY: str = "placeholder_key"
    EMBEDDING_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    EMBEDDING_MODEL: str = "doubao-embedding"
    EMBEDDING_DIMENSION: int = 1024
    
    # 大语言模型配置（对接兼容 OpenAI 规范 of LongCat/火山 LLM）
    LLM_API_KEY: str = "placeholder_key"
    LLM_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    LLM_MODEL: str = "doubao-pro"
    
    # 跨域设置
    ALLOWED_ORIGINS: List[str] = ["*"]

    model_config = ConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def assemble_db_url(self) -> Self:
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self

_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
