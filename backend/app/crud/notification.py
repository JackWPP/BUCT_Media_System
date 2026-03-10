"""
通知 CRUD 操作
"""
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.models.notification import Notification


async def create_notification(
    db: AsyncSession,
    *,
    user_id: str,
    type: str,
    title: str,
    content: Optional[str] = None,
    related_id: Optional[str] = None,
) -> Notification:
    """创建通知"""
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        content=content,
        related_id=related_id,
    )
    db.add(notification)
    await db.flush()
    return notification


async def get_notifications(
    db: AsyncSession,
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    unread_only: bool = False,
) -> Tuple[List[Notification], int]:
    """获取用户的通知列表"""
    query = select(Notification).filter(Notification.user_id == user_id)
    count_query = select(func.count(Notification.id)).filter(Notification.user_id == user_id)

    if unread_only:
        query = query.filter(Notification.is_read == False)  # noqa: E712
        count_query = count_query.filter(Notification.is_read == False)  # noqa: E712

    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return list(notifications), total


async def get_unread_count(db: AsyncSession, user_id: str) -> int:
    """获取未读通知数"""
    result = await db.execute(
        select(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    return result.scalar() or 0


async def mark_as_read(db: AsyncSession, notification_id: str, user_id: str) -> bool:
    """标记单条通知为已读"""
    result = await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user_id)
        .values(is_read=True)
    )
    return result.rowcount > 0


async def mark_all_as_read(db: AsyncSession, user_id: str) -> int:
    """标记所有通知为已读"""
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    return result.rowcount
