"""
System configuration models.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.core.database import Base


class SystemConfig(Base):
    """Simple key-value store for runtime-adjustable system settings."""

    __tablename__ = "system_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String(36))

    def __repr__(self) -> str:
        return f"<SystemConfig(key='{self.key}', value='{self.value}')>"


class ConfigKeys:
    PORTRAIT_VISIBILITY = "portrait_visibility"
    AI_ENABLED = "ai_enabled"
    AI_PROVIDER = "ai_provider"
    AI_MODEL_ID = "ai_model_id"


class PortraitVisibility:
    PUBLIC = "public"
    LOGIN_REQUIRED = "login_required"
    AUTHORIZED_ONLY = "authorized_only"
