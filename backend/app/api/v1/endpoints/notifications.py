"""
通知 API 端点

用户获取自己的通知列表、标记已读。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.crud import notification as notif_crud
from app.models.user import User
from app.schemas.notification import NotificationItem, NotificationList

router = APIRouter()


@router.get("/notifications", response_model=NotificationList)
async def get_my_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取当前用户的通知列表"""
    notifications, total = await notif_crud.get_notifications(
        db, user_id=current_user.id, skip=skip, limit=limit, unread_only=unread_only,
    )
    unread_count = await notif_crud.get_unread_count(db, current_user.id)

    return NotificationList(
        notifications=[NotificationItem.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count,
    )


@router.get("/notifications/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取未读通知数"""
    count = await notif_crud.get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """标记单条通知为已读"""
    success = await notif_crud.mark_as_read(db, notification_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
    await db.commit()
    return {"detail": "已标记为已读"}


@router.put("/notifications/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """标记所有通知为已读"""
    count = await notif_crud.mark_all_as_read(db, current_user.id)
    await db.commit()
    return {"detail": f"已标记 {count} 条通知为已读"}
