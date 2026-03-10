"""
审计日志 Pydantic Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AuditLogItem(BaseModel):
    """单条审计日志"""
    id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None      # 从关联查询填充
    user_student_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    detail: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogList(BaseModel):
    """审计日志列表响应"""
    logs: list[AuditLogItem]
    total: int
