"""
系统配置模型

用于存储系统级别的配置项，如人像照片可见性设置等。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from app.core.database import Base


class SystemConfig(Base):
    """
    系统配置表
    
    用于存储键值对形式的系统配置，支持管理员动态调整系统行为。
    
    配置项示例:
    - portrait_visibility: 人像照片可见性 (public/login_required/authorized_only)
    """
    __tablename__ = "system_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(Text)  # 配置项描述
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String(36))  # 最后修改人 ID

    def __repr__(self):
        return f"<SystemConfig(key='{self.key}', value='{self.value}')>"


# 预定义配置键常量
class ConfigKeys:
    """配置键常量"""
    PORTRAIT_VISIBILITY = "portrait_visibility"


# 预定义配置值常量
class PortraitVisibility:
    """人像照片可见性级别"""
    PUBLIC = "public"              # 公开访问
    LOGIN_REQUIRED = "login_required"  # 需要登录
    AUTHORIZED_ONLY = "authorized_only"  # 仅授权用户
