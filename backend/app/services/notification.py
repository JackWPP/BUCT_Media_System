"""
通知服务

提供便捷方法在业务逻辑中发送通知。
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.notification import create_notification


async def notify_user(
    db: AsyncSession,
    *,
    user_id: str,
    type: str,
    title: str,
    content: Optional[str] = None,
    related_id: Optional[str] = None,
):
    """
    发送站内通知给指定用户

    用法示例:
        await notify_user(db, user_id=uploader_id, type="photo_approved",
                          title="您的照片已通过审核", related_id=photo_id)
    """
    await create_notification(
        db,
        user_id=user_id,
        type=type,
        title=title,
        content=content,
        related_id=related_id,
    )
