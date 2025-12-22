"""
Dependency injection functions

提供 FastAPI 依赖注入函数，用于数据库会话、用户认证和权限校验。
"""
from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.security import decode_access_token
from app.crud import user as user_crud
from app.models.user import User
from app.models.system_config import SystemConfig, ConfigKeys, PortraitVisibility

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency
    
    获取异步数据库会话，用于 CRUD 操作。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from token
    
    从 JWT token 中解析并验证当前用户。
    JWT subject 为 student_id。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    student_id: Optional[str] = payload.get("sub")
    if student_id is None:
        raise credentials_exception
    
    # 优先按 student_id 查找，回退到 email（兼容旧 token）
    user = await user_crud.get_user_by_student_id(db, student_id=student_id)
    if user is None:
        user = await user_crud.get_user_by_email(db, email=student_id)
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    
    验证用户账号是否处于激活状态。
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current admin user (超级管理员)
    
    严格校验用户角色为 admin，用于需要超级管理员权限的接口。
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user


async def get_current_auditor_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current auditor or admin user (审核员或管理员)
    
    校验用户角色为 admin 或 auditor，用于需要审核权限的接口。
    """
    if current_user.role not in ("admin", "auditor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Auditor or Admin role required."
        )
    return current_user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    
    用于公开接口，允许游客访问但可能根据登录状态返回不同内容。
    """
    if not token:
        return None
    
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    student_id: Optional[str] = payload.get("sub")
    if student_id is None:
        return None
    
    # 优先按 student_id 查找，回退到 email
    user = await user_crud.get_user_by_student_id(db, student_id=student_id)
    if user is None:
        user = await user_crud.get_user_by_email(db, email=student_id)
    return user


async def get_system_config(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    获取系统配置
    
    从数据库加载所有系统配置项，返回字典形式。
    如果配置不存在，返回默认值。
    """
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    
    config_dict = {config.key: config.value for config in configs}
    
    # 设置默认值
    if ConfigKeys.PORTRAIT_VISIBILITY not in config_dict:
        config_dict[ConfigKeys.PORTRAIT_VISIBILITY] = PortraitVisibility.LOGIN_REQUIRED
    
    return config_dict


async def get_portrait_visibility(
    config: dict = Depends(get_system_config)
) -> str:
    """
    获取人像照片可见性设置
    
    返回值:
    - public: 公开访问
    - login_required: 需要登录
    - authorized_only: 仅授权用户
    """
    return config.get(ConfigKeys.PORTRAIT_VISIBILITY, PortraitVisibility.LOGIN_REQUIRED)

