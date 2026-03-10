"""
应用配置管理模块
"""
from typing import Literal
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings

# 默认密钥常量，仅用于启动时判断用户是否已自定义配置
DEFAULT_SECRET_KEY = "your-secret-key-here-change-in-production"


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
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Access Token 短时效
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # Refresh Token 长时效
    
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
    
    # SSO/OAuth 预留配置（对接学校统一身份认证）
    # 认证流程类似 Google OAuth: authorize → callback → token → userinfo
    SSO_ENABLED: bool = False
    SSO_PROVIDER: str = "university_sso"  # 认证提供方标识
    SSO_CLIENT_ID: str | None = None
    SSO_CLIENT_SECRET: str | None = None
    SSO_AUTHORIZE_URL: str | None = None    # 学校认证页面 URL
    SSO_TOKEN_URL: str | None = None        # 获取 Token 的 URL
    SSO_USERINFO_URL: str | None = None     # 获取用户信息的 URL
    SSO_REDIRECT_URI: str = "http://localhost:5173/auth/callback"
    SSO_SCOPES: str = "openid profile email"
    SSO_AUTO_CREATE_USER: bool = True       # SSO 登录时自动创建本地用户

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
