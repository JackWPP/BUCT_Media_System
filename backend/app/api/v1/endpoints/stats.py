"""
统计相关 API
"""
from typing import Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, select
from app.core import deps
from app.models.photo import Photo
from app.models.tag import Tag, PhotoTag
from app.models.user import User

router = APIRouter()

# 简单的内存级防刷缓存: {(ip, photo_id): last_view_time}
_view_cache: dict[tuple[str, str], datetime] = {}
VIEW_COOLDOWN_MINUTES = 5


def _get_client_ip(request: Request) -> str:
    """获取客户端真实 IP"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _should_count_view(client_ip: str, photo_id: str) -> bool:
    """检查是否应该计入浏览量（基于 IP 的冷却时间）"""
    key = (client_ip, photo_id)
    now = datetime.utcnow()
    last_view = _view_cache.get(key)

    if last_view is None:
        _view_cache[key] = now
        return True

    if now - last_view >= timedelta(minutes=VIEW_COOLDOWN_MINUTES):
        _view_cache[key] = now
        return True

    return False


@router.post("/view/{photo_id}")
async def increment_view(
    photo_id: str,
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Increment view count for a photo
    """
    result = await db.execute(select(Photo).filter(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # 防刷检查：同一 IP 在冷却时间内不重复计数
    client_ip = _get_client_ip(request)
    if not _should_count_view(client_ip, photo_id):
        return {"message": "View count not incremented (cooldown)", "views": photo.views or 0}

    # 使用 coalesce 处理可能的 None 值
    current_views = photo.views if photo.views is not None else 0
    photo.views = current_views + 1
    await db.commit()
    return {"message": "View count incremented", "views": photo.views}

@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_auditor_user),
):
    """
    Get dashboard statistics (reviewer only)
    """
    # 1. Total Photos
    result = await db.execute(
        select(func.count(Photo.id)).filter(Photo.status != "deleted")
    )
    total_photos = result.scalar() or 0

    # 2. Total Views
    result = await db.execute(
        select(func.sum(Photo.views))
    )
    total_views = result.scalar() or 0

    # 3. Storage Usage
    result = await db.execute(
        select(func.sum(Photo.file_size)).filter(Photo.status != "deleted")
    )
    total_storage = result.scalar() or 0

    # 4. Daily Uploads (Last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    result = await db.execute(
        select(
            func.date(Photo.created_at).label('date'),
            func.count(Photo.id).label('count')
        ).filter(
            Photo.created_at >= thirty_days_ago,
            Photo.status != "deleted"
        ).group_by(
            func.date(Photo.created_at)
        )
    )
    daily_uploads = result.all()

    # 5. Popular Tags
    result = await db.execute(
        select(Tag.name, Tag.usage_count).order_by(desc(Tag.usage_count)).limit(20)
    )
    popular_tags = result.all()

    # 6. Top Viewed Photos
    result = await db.execute(
        select(Photo).filter(
            Photo.status == "approved"
        ).order_by(desc(Photo.views)).limit(10)
    )
    top_photos = result.scalars().all()

    return {
        "total_photos": total_photos,
        "total_views": total_views,
        "total_storage": total_storage,
        "daily_uploads": [{"date": str(d.date), "count": d.count} for d in daily_uploads],
        "popular_tags": [{"name": t.name, "count": t.usage_count} for t in popular_tags],
        "top_photos": [{
            "id": p.id,
            "filename": p.filename,
            "views": p.views or 0,
            "thumb_path": p.thumb_path
        } for p in top_photos]
    }
