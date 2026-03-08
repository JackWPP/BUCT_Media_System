"""
应用配置管理模块
"""
from typing import Literal
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    APP_NAME: str = "BUCT Media HUB"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./buct_media.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    TASK_QUEUE_BACKEND: Literal["background", "celery"] = "background"
    
    # 文件存储配置
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 20971520  # 20MB
    S3_ENDPOINT: str | None = None
    S3_BUCKET: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_REGION: str | None = None
    S3_USE_SSL: bool = False
    S3_PRESIGN_EXPIRE_SECONDS: int = 600
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AI 服务配置
    AI_PROVIDER: Literal["ollama", "dashscope", "openai_compatible"] = "ollama"
    OLLAMA_API_URL: str = "http://localhost:11434"
    AI_MODEL_NAME: str = "llava"
    AI_MODEL_ID: str = "llava"
    AI_ENABLED: bool = True
    AI_TIMEOUT: int = 60
    AI_MAX_RETRIES: int = 2
    AI_DAILY_BUDGET: int = 500
    DASHSCOPE_API_KEY: str | None = None
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    OPENAI_COMPATIBLE_API_KEY: str | None = None
    OPENAI_COMPATIBLE_BASE_URL: str | None = None
    OPENAI_COMPATIBLE_MODEL_ID: str | None = None
    OPENAI_COMPATIBLE_HEADERS: dict[str, str] = Field(default_factory=dict)
    
    # CORS 配置
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
