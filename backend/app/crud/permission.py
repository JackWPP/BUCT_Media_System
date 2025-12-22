"""
权限 CRUD 操作
"""
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.permission import ResourcePermission, ResourceType, PermissionType
from app.models.user import User


async def create_permission(
    db: AsyncSession,
    user_id: str,
    resource_type: str,
    resource_key: str,
    permission_type: str = "view",
    days: Optional[int] = 30,
    note: Optional[str] = None,
    created_by: Optional[str] = None
) -> ResourcePermission:
    """
    创建权限
    
    Args:
        user_id: 被授权用户 ID
        resource_type: 资源类型 (category/photo/tag)
        resource_key: 资源键值 (如 Portrait)
        permission_type: 权限类型 (view/download/upload)
        days: 授权天数，None 表示永久
        note: 备注
        created_by: 授权人 ID
    """
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(days=days) if days else None
    
    permission = ResourcePermission(
        user_id=user_id,
        resource_type=ResourceType(resource_type),
        resource_key=resource_key,
        permission_type=PermissionType(permission_type),
        start_time=start_time,
        end_time=end_time,
        note=note,
        created_by=created_by
    )
    
    db.add(permission)
    await db.commit()
    await db.refresh(permission)
    return permission


async def get_user_permissions(
    db: AsyncSession,
    user_id: str,
    active_only: bool = True
) -> List[ResourcePermission]:
    """
    获取用户的所有权限
    """
    query = select(ResourcePermission).filter(ResourcePermission.user_id == user_id)
    
    if active_only:
        now = datetime.utcnow()
        query = query.filter(
            and_(
                ResourcePermission.start_time <= now,
                (ResourcePermission.end_time.is_(None)) | (ResourcePermission.end_time > now)
            )
        )
    
    result = await db.execute(query.order_by(ResourcePermission.created_at.desc()))
    return list(result.scalars().all())


async def check_permission(
    db: AsyncSession,
    user_id: str,
    resource_type: str,
    resource_key: str,
    permission_type: str = "view"
) -> bool:
    """
    检查用户是否有特定资源的权限
    """
    now = datetime.utcnow()
    query = select(ResourcePermission).filter(
        and_(
            ResourcePermission.user_id == user_id,
            ResourcePermission.resource_type == ResourceType(resource_type),
            ResourcePermission.resource_key == resource_key,
            ResourcePermission.permission_type == PermissionType(permission_type),
            ResourcePermission.start_time <= now,
            (ResourcePermission.end_time.is_(None)) | (ResourcePermission.end_time > now)
        )
    )
    
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def delete_permission(db: AsyncSession, permission_id: str) -> bool:
    """
    删除权限
    """
    result = await db.execute(
        select(ResourcePermission).filter(ResourcePermission.id == permission_id)
    )
    permission = result.scalar_one_or_none()
    
    if not permission:
        return False
    
    await db.delete(permission)
    await db.commit()
    return True


async def get_all_permissions(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None
) -> Tuple[List[ResourcePermission], int]:
    """
    获取所有权限（分页）
    """
    query = select(ResourcePermission)
    count_query = select(func.count(ResourcePermission.id))
    
    if user_id:
        query = query.filter(ResourcePermission.user_id == user_id)
        count_query = count_query.filter(ResourcePermission.user_id == user_id)
    
    if resource_type:
        query = query.filter(ResourcePermission.resource_type == ResourceType(resource_type))
        count_query = count_query.filter(ResourcePermission.resource_type == ResourceType(resource_type))
    
    query = query.order_by(ResourcePermission.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    permissions = list(result.scalars().all())
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    return permissions, total
