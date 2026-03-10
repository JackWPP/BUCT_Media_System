"""
审计日志 CRUD 操作
"""
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.audit_log import AuditLog


async def create_audit_log(
    db: AsyncSession,
    *,
    user_id: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    创建审计日志记录

    Args:
        user_id: 操作用户 ID
        action: 操作类型（如 photo.approve, user.delete）
        resource_type: 资源类型
        resource_id: 资源 ID
        detail: 操作详情
        ip_address: 请求 IP
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(log)
    await db.flush()  # 仅 flush，不 commit，由上层控制事务
    return log


async def get_audit_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Tuple[List[AuditLog], int]:
    """
    查询审计日志（支持多条件筛选和分页）
    """
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
        count_query = count_query.filter(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
        count_query = count_query.filter(AuditLog.user_id == user_id)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
        count_query = count_query.filter(AuditLog.resource_type == resource_type)
    if start_time:
        query = query.filter(AuditLog.created_at >= start_time)
        count_query = count_query.filter(AuditLog.created_at >= start_time)
    if end_time:
        query = query.filter(AuditLog.created_at <= end_time)
        count_query = count_query.filter(AuditLog.created_at <= end_time)

    query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return list(logs), total
