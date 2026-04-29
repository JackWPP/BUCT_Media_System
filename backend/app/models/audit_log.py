"""
审计日志模型

记录系统中的关键操作，用于安全审计和问题追溯。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class AuditLog(Base):
    """
    审计日志表

    记录用户的关键操作，如审核、删除、权限变更、用户管理等。

    Attributes:
        action: 操作类型（如 photo.approve, user.delete, permission.grant）
        resource_type: 资源类型（如 photo, user, permission）
        resource_id: 被操作的资源 ID
        detail: 操作详情（JSON 字符串或文本描述）
        ip_address: 操作者 IP 地址
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True, comment="操作类型")
    resource_type = Column(String(50), nullable=True, index=True, comment="资源类型")
    resource_id = Column(String(36), nullable=True, comment="资源ID")
    detail = Column(Text, nullable=True, comment="操作详情")
    ip_address = Column(String(45), nullable=True, comment="IP地址")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关系
    user = relationship("User", backref="audit_logs", lazy="selectin")

    # 复合索引：按时间+操作类型查询
    __table_args__ = (
        Index("ix_audit_logs_created_action", "created_at", "action"),
    )

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', user_id='{self.user_id}', resource='{self.resource_type}:{self.resource_id}')>"
