"""
通知 Pydantic Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NotificationItem(BaseModel):
    """单条通知"""
    id: str
    type: str
    title: str
    content: Optional[str] = None
    is_read: bool
    related_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationList(BaseModel):
    """通知列表响应"""
    notifications: list[NotificationItem]
    total: int
    unread_count: int
