"""
系统配置 API 端点

仅限超级管理员访问，用于管理系统级别配置。
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_db, get_current_admin_user
from app.models.user import User
from app.models.system_config import SystemConfig, ConfigKeys, PortraitVisibility

router = APIRouter(prefix="/settings", tags=["系统设置"])


# ================= Schemas =================

class PortraitVisibilityUpdate(BaseModel):
    """
    人像照片可见性更新 schema
    """
    visibility: str  # public, login_required, authorized_only
    
    class Config:
        json_schema_extra = {
            "example": {
                "visibility": "login_required"
            }
        }


class SystemSettings(BaseModel):
    """
    系统设置响应 schema
    """
    portrait_visibility: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "portrait_visibility": "login_required"
            }
        }


# ================= Helper Functions =================

async def get_or_create_config(db: AsyncSession, key: str, default_value: str) -> SystemConfig:
    """
    获取配置项，如果不存在则创建默认值
    """
    result = await db.execute(select(SystemConfig).filter(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    
    if not config:
        config = SystemConfig(
            key=key,
            value=default_value,
            description=f"System config for {key}"
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
    
    return config


# ================= Endpoints =================

@router.get("", response_model=SystemSettings)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    """
    获取系统设置
    
    - 仅限管理员访问
    """
    portrait_config = await get_or_create_config(
        db, 
        ConfigKeys.PORTRAIT_VISIBILITY, 
        PortraitVisibility.LOGIN_REQUIRED
    )
    
    return SystemSettings(
        portrait_visibility=portrait_config.value
    )


@router.put("/portrait-visibility", response_model=SystemSettings)
async def update_portrait_visibility(
    data: PortraitVisibilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    更新人像照片可见性设置
    
    - 仅限管理员访问
    - 可选值: public（公开）, login_required（需要登录）, authorized_only（仅授权用户）
    """
    # 验证可见性值
    valid_values = [
        PortraitVisibility.PUBLIC,
        PortraitVisibility.LOGIN_REQUIRED,
        PortraitVisibility.AUTHORIZED_ONLY,
    ]
    
    if data.visibility not in valid_values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的可见性设置。可选值: {', '.join(valid_values)}"
        )
    
    # 获取或创建配置
    config = await get_or_create_config(
        db,
        ConfigKeys.PORTRAIT_VISIBILITY,
        PortraitVisibility.LOGIN_REQUIRED
    )
    
    # 更新配置
    config.value = data.visibility
    config.updated_by = current_user.id
    
    await db.commit()
    await db.refresh(config)
    
    return SystemSettings(portrait_visibility=config.value)


@router.get("/portrait-visibility")
async def get_portrait_visibility_public(
    db: AsyncSession = Depends(get_db),
):
    """
    获取人像照片可见性设置（公开接口）
    
    - 用于前端判断是否显示人像分类
    """
    result = await db.execute(
        select(SystemConfig).filter(SystemConfig.key == ConfigKeys.PORTRAIT_VISIBILITY)
    )
    config = result.scalar_one_or_none()
    
    visibility = config.value if config else PortraitVisibility.LOGIN_REQUIRED
    
    return {"portrait_visibility": visibility}
