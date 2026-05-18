import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Default values taken from 04.py as fallback if not in environment
    openai_api_key: str = "ak_2kv4sp70L7Ey8DD7h61308un1TS62"
    openai_base_url: str = "https://api.longcat.chat/openai/v1"
    model_name: str = "longcat-flash-chat"
    
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Allows setting values via environment variables prefixed with APP_
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        case_sensitive=False
    )

settings = Settings()
