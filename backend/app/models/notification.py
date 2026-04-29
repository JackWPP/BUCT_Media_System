"""
站内通知模型

支持通知用户照片审核结果、权限变更等系统事件。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class Notification(Base):
    """
    通知表

    Attributes:
        type: 通知类型 (photo_approved/photo_rejected/permission_granted/system)
        title: 通知标题
        content: 通知内容
        is_read: 是否已读
        related_id: 关联资源 ID（如照片 ID）
    """
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True, comment="通知类型")
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    related_id = Column(String(36), nullable=True, comment="关联资源ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关系
    user = relationship("User", backref="notifications")

    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
    )

    def __repr__(self):
        return f"<Notification(type='{self.type}', user_id='{self.user_id}', read={self.is_read})>"
