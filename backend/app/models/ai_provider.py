"""
AI provider runtime configuration models.
"""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text

from app.core.database import Base


class AIProviderType:
    OLLAMA = "ollama"
    DASHSCOPE = "dashscope"
    OPENAI_COMPATIBLE = "openai_compatible"

    ALL = {OLLAMA, DASHSCOPE, OPENAI_COMPATIBLE}


class AIProviderConfig(Base):
    """Database-managed AI provider settings."""

    __tablename__ = "ai_provider_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_type = Column(String(50), nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    base_url = Column(String(500), nullable=False)
    model_id = Column(String(200), nullable=False)
    api_key_encrypted = Column(Text)
    extra_headers_json = Column(JSON)
    timeout_seconds = Column(Integer, default=60, nullable=False)
    max_retries = Column(Integer, default=2, nullable=False)
    daily_budget = Column(Integer, default=500, nullable=False)
    last_test_status = Column(String(20))
    last_test_message = Column(Text)
    last_tested_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(36))
    updated_by = Column(String(36))

    def __repr__(self) -> str:
        return f"<AIProviderConfig(id='{self.id}', provider_type='{self.provider_type}', default={self.is_default})>"
