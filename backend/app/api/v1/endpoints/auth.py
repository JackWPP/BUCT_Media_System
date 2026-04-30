import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db, get_current_active_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.schemas.token import LoginRequest, LoginResponse, RefreshRequest, Token
from app.schemas.user import User, UserCreate, PasswordChange
from app.crud import user as user_crud

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录

    支持学号或邮箱登录，返回 Access Token、Refresh Token 和用户信息。
    """
    # 先查找用户（不校验密码）以支持失败计数
    from app.crud.user import get_user_by_email, get_user_by_student_id
    user = await get_user_by_email(db, credentials.identifier)
    if not user:
        user = await get_user_by_student_id(db, credentials.identifier)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="学号/邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查账号是否被锁定
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被锁定，请15分钟后再试"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )

    # 校验密码
    if not user_crud.verify_password(credentials.password, user.hashed_password):
        await user_crud.record_login_failure(db, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="学号/邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 登录成功，记录审计信息
    await user_crud.record_login_success(db, user)

    # 使用 student_id 作为 JWT subject (主要标识)，携带 token_version
    token_data = {"sub": user.student_id, "ver": user.token_version}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=User.model_validate(user)
    )


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前登录用户信息
    """
    return current_user


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 兼容的 token 登录端点

    username 字段可以是学号或邮箱。
    """
    from app.crud.user import get_user_by_email, get_user_by_student_id
    user = await get_user_by_email(db, form_data.username)
    if not user:
        user = await get_user_by_student_id(db, form_data.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="学号/邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被锁定，请15分钟后再试"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )

    if not user_crud.verify_password(form_data.password, user.hashed_password):
        await user_crud.record_login_failure(db, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="学号/邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await user_crud.record_login_success(db, user)

    # 使用 student_id 作为 JWT subject，携带 token_version
    token_data = {"sub": user.student_id, "ver": user.token_version}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/refresh", response_model=Token)
@limiter.limit("30/minute")
async def refresh_access_token(
    request: Request,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    使用 Refresh Token 获取新的 Access Token

    Refresh Token 过期后用户需重新登录。
    """
    payload = decode_refresh_token(body.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    student_id = payload.get("sub")
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 格式无效",
        )

    # 验证用户仍然存在且活跃
    user = await user_crud.get_user_by_student_id(db, student_id=student_id)
    if user is None:
        user = await user_crud.get_user_by_email(db, email=student_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
        )

    # 校验 token_version，防止旧 Refresh Token 在密码修改后仍可用
    token_ver = payload.get("ver")
    if token_ver is not None and token_ver != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 签发新的 Token 对
    token_data = {"sub": user.student_id, "ver": user.token_version}
    new_access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data=token_data)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.put("/password")
async def change_password(
    body: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    用户自助修改密码

    需提供旧密码验证。
    """
    success = await user_crud.change_user_password(
        db,
        user_id=current_user.id,
        old_password=body.old_password,
        new_password=body.new_password,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误",
        )
    return {"detail": "密码修改成功"}


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    用户注册

    必须提供学号，邮箱可选。
    若开启注册审批 (REQUIRE_REGISTRATION_APPROVAL=True)，
    新注册用户 is_active=False，需管理员审批后方可登录。
    """
    from app.core.config import get_settings
    settings = get_settings()

    # 检查学号是否已存在
    existing_user = await user_crud.get_user_by_student_id(db, user_data.student_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该学号已被注册"
        )

    # 如果提供了邮箱，检查邮箱是否已存在
    if user_data.email:
        existing_email = await user_crud.get_user_by_email(db, user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该邮箱已被注册"
            )

    # 创建新用户，若开启审批则默认禁用
    is_active = not settings.REQUIRE_REGISTRATION_APPROVAL
    new_user = await user_crud.create_user(db, user_data, role="user")
    if not is_active:
        new_user.is_active = False
        await db.commit()
        await db.refresh(new_user)

    return User.model_validate(new_user)
