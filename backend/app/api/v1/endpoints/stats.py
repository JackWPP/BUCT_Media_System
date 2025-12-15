"""
统计相关 API
"""
from typing import Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, select
from app.core import deps
from app.models.photo import Photo
from app.models.tag import Tag, PhotoTag
from app.models.user import User

router = APIRouter()

@router.post("/view/{photo_id}")
async def increment_view(
    photo_id: str,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Increment view count for a photo
    """
    result = await db.execute(select(Photo).filter(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    # 使用 coalesce 处理可能的 None 值
    current_views = photo.views if photo.views is not None else 0
    photo.views = current_views + 1
    await db.commit()
    return {"message": "View count incremented", "views": photo.views}

@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user),
):
    """
    Get dashboard statistics (admin only)
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
