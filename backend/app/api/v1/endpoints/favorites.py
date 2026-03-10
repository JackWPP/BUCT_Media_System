"""
照片收藏 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.crud import favorite as fav_crud
from app.crud import photo as photo_crud
from app.models.user import User

router = APIRouter()


@router.post("/{photo_id}/favorite")
async def toggle_favorite(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    切换照片收藏状态

    - 如果未收藏，则收藏
    - 如果已收藏，则取消收藏
    """
    photo = await photo_crud.get_photo(db, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    is_now_favorited = await fav_crud.toggle_favorite(db, current_user.id, photo_id)
    count = await fav_crud.get_photo_favorite_count(db, photo_id)

    return {
        "favorited": is_now_favorited,
        "favorite_count": count,
    }


@router.get("/{photo_id}/favorite")
async def get_favorite_status(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取照片收藏状态"""
    is_fav = await fav_crud.is_favorited(db, current_user.id, photo_id)
    count = await fav_crud.get_photo_favorite_count(db, photo_id)
    return {"favorited": is_fav, "favorite_count": count}


@router.get("/favorites/my")
async def get_my_favorites(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取我的收藏列表"""
    photo_ids, total = await fav_crud.get_user_favorites(
        db, current_user.id, skip=skip, limit=limit,
    )
    return {"photo_ids": photo_ids, "total": total}
