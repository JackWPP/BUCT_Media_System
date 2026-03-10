"""
用户个人中心和照片收藏 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.deps import get_db, get_current_active_user
from app.crud import user as user_crud
from app.models.user import User
from app.schemas.user import User as UserSchema, UserUpdate

router = APIRouter()


@router.get("/profile", response_model=UserSchema)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
):
    """获取当前用户个人信息"""
    return UserSchema.model_validate(current_user)


@router.put("/profile", response_model=UserSchema)
async def update_my_profile(
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新当前用户个人信息

    可修改邮箱和姓名（不包含密码，密码走 PUT /auth/password）。
    """
    # 排除密码字段，密码修改走专用端点
    update_data = user_data.model_dump(exclude_unset=True, exclude={"password"})

    if "email" in update_data and update_data["email"]:
        existing = await user_crud.get_user_by_email(db, update_data["email"])
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该邮箱已被其他用户使用",
            )

    for key, value in update_data.items():
        setattr(current_user, key, value)

    await db.commit()
    await db.refresh(current_user)
    return UserSchema.model_validate(current_user)
