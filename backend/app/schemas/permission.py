"""
权限管理 Pydantic schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum


class ResourceTypeEnum(str, Enum):
    """资源类型"""
    CATEGORY = "category"
    PHOTO = "photo"
    TAG = "tag"


class PermissionTypeEnum(str, Enum):
    """权限类型"""
    VIEW = "view"
    DOWNLOAD = "download"
    UPLOAD = "upload"


class PermissionCreate(BaseModel):
    """创建权限请求"""
    user_id: str
    resource_type: ResourceTypeEnum
    resource_key: str  # 如 'Portrait' 或照片 ID
    permission_type: PermissionTypeEnum = PermissionTypeEnum.VIEW
    end_time: Optional[datetime] = None  # None 表示永久
    note: Optional[str] = None


class PermissionResponse(BaseModel):
    """权限响应"""
    id: str
    user_id: str
    user_student_id: Optional[str] = None
    user_name: Optional[str] = None
    resource_type: str
    resource_key: str
    permission_type: str
    start_time: datetime
    end_time: Optional[datetime]
    is_active: bool
    created_at: datetime
    note: Optional[str]
    
    class Config:
        from_attributes = True


class PermissionList(BaseModel):
    """权限列表响应"""
    permissions: List[PermissionResponse]
    total: int


class PermissionGrantRequest(BaseModel):
    """
    授权请求 - 简化版
    
    管理员可以按学号授权访问特定类别。
    """
    student_id: str  # 被授权用户的学号
    resource_type: ResourceTypeEnum = ResourceTypeEnum.CATEGORY
    resource_key: str = "Portrait"  # 默认授权访问 Portrait
    permission_type: PermissionTypeEnum = PermissionTypeEnum.VIEW
    days: Optional[int] = 30  # 授权天数，None 表示永久
    note: Optional[str] = None
