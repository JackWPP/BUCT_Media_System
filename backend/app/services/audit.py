"""
审计日志工具函数

提供便捷的审计日志记录方法，在关键操作调用点手动调用即可。
"""
from typing import Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.audit_log import create_audit_log


async def log_audit(
    db: AsyncSession,
    *,
    user_id: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    detail: Optional[str] = None,
    request: Optional[Request] = None,
):
    """
    记录审计日志的便捷方法

    用法示例:
        await log_audit(db, user_id=user.id, action="photo.approve",
                        resource_type="photo", resource_id=photo_id)
    """
    ip_address = None
    if request:
        ip_address = request.client.host if request.client else None

    await create_audit_log(
        db,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
    )
