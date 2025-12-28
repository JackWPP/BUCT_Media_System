"""
权限管理 API 端点

管理员可以给用户（按学号）授予特定资源的限时访问权限。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.core.deps import get_db, get_current_admin_user
from app.models.user import User
from app.crud import user as user_crud
from app.crud import permission as permission_crud
from app.schemas.permission import (
    PermissionGrantRequest,
    PermissionResponse,
    PermissionList,
)

router = APIRouter(prefix="/permissions", tags=["permission-management"])


@router.post("/grant", response_model=PermissionResponse)
async def grant_permission(
    request: PermissionGrantRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    授予用户权限
    
    管理员可以按学号给用户授权访问特定资源（如 Portrait 类别）。
    """
    # 查找用户
    target_user = await user_crud.get_user_by_student_id(db, request.student_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"学号 {request.student_id} 对应的用户不存在"
        )
    
    # 创建权限
    permission = await permission_crud.create_permission(
        db=db,
        user_id=target_user.id,
        resource_type=request.resource_type.value,
        resource_key=request.resource_key,
        permission_type=request.permission_type.value,
        days=request.days,
        note=request.note,
        created_by=current_admin.id
    )
    
    # 计算是否在有效期内
    now = datetime.utcnow()
    is_active = permission.start_time <= now and (
        permission.end_time is None or permission.end_time > now
    )
    
    return PermissionResponse(
        id=permission.id,
        user_id=permission.user_id,
        user_student_id=target_user.student_id,
        user_name=target_user.full_name,
        resource_type=permission.resource_type.value,
        resource_key=permission.resource_key,
        permission_type=permission.permission_type.value,
        start_time=permission.start_time,
        end_time=permission.end_time,
        is_active=is_active,
        created_at=permission.created_at,
        note=permission.note
    )


@router.get("/user/{student_id}", response_model=PermissionList)
async def get_user_permissions(
    student_id: str,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    获取用户的权限列表
    
    按学号查询用户的所有授权记录。
    """
    # 查找用户
    target_user = await user_crud.get_user_by_student_id(db, student_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"学号 {student_id} 对应的用户不存在"
        )
    
    permissions = await permission_crud.get_user_permissions(
        db, target_user.id, active_only=active_only
    )
    
    now = datetime.utcnow()
    result = []
    for p in permissions:
        is_active = p.start_time <= now and (p.end_time is None or p.end_time > now)
        result.append(PermissionResponse(
            id=p.id,
            user_id=p.user_id,
            user_student_id=target_user.student_id,
            user_name=target_user.full_name,
            resource_type=p.resource_type.value,
            resource_key=p.resource_key,
            permission_type=p.permission_type.value,
            start_time=p.start_time,
            end_time=p.end_time,
            is_active=is_active,
            created_at=p.created_at,
            note=p.note
        ))
    
    return PermissionList(permissions=result, total=len(result))


@router.delete("/{permission_id}")
async def revoke_permission(
    permission_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    撤销权限
    """
    deleted = await permission_crud.delete_permission(db, permission_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="权限不存在"
        )
    
    return {"message": "权限已撤销"}


@router.get("/check/{student_id}")
async def check_user_permission(
    student_id: str,
    resource_type: str = "category",
    resource_key: str = "Portrait",
    permission_type: str = "view",
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    检查用户是否有特定权限
    """
    target_user = await user_crud.get_user_by_student_id(db, student_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"学号 {student_id} 对应的用户不存在"
        )
    
    has_permission = await permission_crud.check_permission(
        db, target_user.id, resource_type, resource_key, permission_type
    )
    
    return {
        "student_id": student_id,
        "resource_type": resource_type,
        "resource_key": resource_key,
        "permission_type": permission_type,
        "has_permission": has_permission
    }
