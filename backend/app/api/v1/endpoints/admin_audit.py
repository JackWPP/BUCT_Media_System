"""
审计日志 API 端点

仅限管理员访问。
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_admin_user
from app.crud import audit_log as audit_crud
from app.models.user import User
from app.schemas.audit_log import AuditLogItem, AuditLogList

router = APIRouter(prefix="/audit-logs")


@router.get("", response_model=AuditLogList)
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None, description="操作类型筛选"),
    user_id: Optional[str] = Query(None, description="操作人 ID"),
    resource_type: Optional[str] = Query(None, description="资源类型筛选"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    """
    查询审计日志

    - 仅限管理员访问
    - 支持按操作类型、用户、资源类型筛选
    """
    logs, total = await audit_crud.get_audit_logs(
        db,
        skip=skip,
        limit=limit,
        action=action,
        user_id=user_id,
        resource_type=resource_type,
    )

    items = []
    for log in logs:
        item = AuditLogItem(
            id=log.id,
            user_id=log.user_id,
            user_name=log.user.full_name if log.user else None,
            user_student_id=log.user.student_id if log.user else None,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            detail=log.detail,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )
        items.append(item)

    return AuditLogList(logs=items, total=total)
