"""
用户管理 API 端点

仅限超级管理员访问，用于用户的增删改查、角色管理和密码重置。
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_admin_user
from app.crud import user as user_crud
from app.models.user import User
from app.services.audit import log_audit
from app.schemas.user import (
    User as UserSchema,
    UserList,
    UserCreateByAdmin,
    UserUpdateByAdmin,
    UserRoleUpdate,
    AdminPasswordReset,
)

router = APIRouter(prefix="/users")


@router.get("", response_model=UserList)
async def get_users(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    search: Optional[str] = Query(None, description="搜索关键词（邮箱或姓名）"),
    role: Optional[str] = Query(None, description="按角色过滤"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    """
    获取用户列表

    - 仅限管理员访问
    - 支持分页和搜索
    """
    users, total = await user_crud.get_users(db, skip=skip, limit=limit, search=search, role=role)
    return UserList(users=[UserSchema.model_validate(u) for u in users], total=total)


@router.post("", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateByAdmin,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    创建新用户

    - 仅限管理员访问
    - 支持指定用户角色（包括创建管理员）
    """
    existing_user = await user_crud.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )

    new_user = await user_crud.create_user_by_admin(db, user_data)
    await log_audit(db, user_id=current_user.id, action="user.create",
                    resource_type="user", resource_id=new_user.id,
                    detail=f"创建用户: {user_data.email} (角色: {user_data.role.value})",
                    request=request)
    await db.commit()
    return UserSchema.model_validate(new_user)


@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    """
    获取单个用户详情

    - 仅限管理员访问
    """
    user = await user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return UserSchema.model_validate(user)


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: str,
    user_data: UserUpdateByAdmin,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    更新用户信息

    - 仅限管理员访问
    - 可修改邮箱、姓名、密码、激活状态和角色
    """
    target_user = await user_crud.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if user_data.email and user_data.email != target_user.email:
        existing = await user_crud.get_user_by_email(db, user_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该邮箱已被其他用户使用"
            )

    updated_user = await user_crud.update_user_by_admin(db, user_id, user_data)
    return UserSchema.model_validate(updated_user)


@router.put("/{user_id}/role", response_model=UserSchema)
async def update_user_role(
    user_id: str,
    role_data: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    修改用户角色

    - 仅限管理员访问
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的角色"
        )

    target_user = await user_crud.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    updated_user = await user_crud.update_user_role(db, user_id, role_data.role.value)
    return UserSchema.model_validate(updated_user)


@router.put("/{user_id}/password")
async def admin_reset_password(
    user_id: str,
    body: AdminPasswordReset,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    管理员重置用户密码

    - 仅限管理员访问
    - 无需旧密码，直接设置新密码
    """
    target_user = await user_crud.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    success = await user_crud.reset_user_password(db, user_id, body.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码重置失败"
        )
    await log_audit(db, user_id=current_user.id, action="user.password_reset",
                    resource_type="user", resource_id=user_id,
                    detail=f"管理员重置用户密码: {target_user.student_id}",
                    request=request)
    await db.commit()
    return {"detail": f"用户 {target_user.student_id} 的密码已重置"}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    删除用户

    - 仅限管理员访问
    - 管理员不能删除自己
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账号"
        )

    target_user = await user_crud.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    await log_audit(db, user_id=current_user.id, action="user.delete",
                    resource_type="user", resource_id=user_id,
                    detail=f"删除用户: {target_user.student_id} ({target_user.email})",
                    request=request)
    success = await user_crud.delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除用户失败"
        )
    return None
