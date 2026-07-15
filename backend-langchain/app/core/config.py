from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "NovaMind-LangChain"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库连接（异步 postgresql）
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/novamind"
    
    # 字节火山引擎 Embedding 配置
    EMBEDDING_API_KEY: str = "placeholder_key"
    EMBEDDING_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    EMBEDDING_MODEL: str = "doubao-embedding"
    EMBEDDING_DIMENSION: int = 1024
    
    # 大语言模型配置（对接兼容 OpenAI 规范的 LongCat/火山 LLM）
    LLM_API_KEY: str = "placeholder_key"
    LLM_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    LLM_MODEL: str = "doubao-pro"
    
    # 跨域设置
    ALLOWED_ORIGINS: List[str] = ["*"]

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
