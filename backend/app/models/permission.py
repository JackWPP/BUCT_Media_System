"""
资源权限模型

用于实现基于学号的精细化、时效性授权。
支持按资源类别（如 Portrait）和时间范围授予特定用户访问权限。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class ResourceType(str, enum.Enum):
    """资源类型"""
    CATEGORY = "category"  # 照片类别（如 Portrait）
    PHOTO = "photo"        # 单张照片
    TAG = "tag"            # 标签


class PermissionType(str, enum.Enum):
    """权限类型"""
    VIEW = "view"          # 查看权限
    DOWNLOAD = "download"  # 下载权限
    UPLOAD = "upload"      # 上传权限（预留）


class ResourcePermission(Base):
    """
    资源权限表
    
    实现基于学号/用户的精细化授权：
    - 管理员可授予特定用户访问受限资源（如 Portrait 类别）的权限
    - 支持时效控制（start_time, end_time）
    
    示例：
    - user_id=123, resource_type='category', resource_key='Portrait', 
      permission_type='view', start_time=now, end_time=now+30days
      表示：用户 123（根据学号对应）在 30 天内可查看 Portrait 类别照片
    """
    __tablename__ = "resource_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 被授权用户
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 资源类型和键
    resource_type = Column(SQLEnum(ResourceType), nullable=False, comment="资源类型")
    resource_key = Column(String(100), nullable=False, index=True, comment="资源键值，如类别名 Portrait 或照片 ID")
    
    # 权限类型
    permission_type = Column(SQLEnum(PermissionType), default=PermissionType.VIEW, nullable=False)
    
    # 时效控制
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False, comment="权限生效时间")
    end_time = Column(DateTime, nullable=True, comment="权限过期时间，NULL 表示永久")
    
    # 审计信息
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True, comment="授权人")
    note = Column(String(500), nullable=True, comment="备注")
    
    # 关系
    user = relationship("User", back_populates="permissions", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<ResourcePermission(user={self.user_id}, type={self.resource_type}, key={self.resource_key}, until={self.end_time})>"
    
    def is_active(self) -> bool:
        """检查权限是否在有效期内"""
        now = datetime.utcnow()
        if self.start_time > now:
            return False
        if self.end_time and self.end_time < now:
            return False
        return True
