"""
Authentication API endpoints

支持学号/邮箱登录。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db, get_current_active_user
from app.core.security import create_access_token
from app.schemas.token import LoginRequest, LoginResponse, Token
from app.schemas.user import User, UserCreate
from app.crud import user as user_crud

router = APIRouter(tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录
    
    支持学号或邮箱登录，返回 JWT token 和用户信息。
    """
    user = await user_crud.authenticate_user(db, credentials.identifier, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="学号/邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    
    # 使用 student_id 作为 JWT subject (主要标识)
    access_token = create_access_token(data={"sub": user.student_id})
    
    return LoginResponse(
        access_token=access_token,
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
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 兼容的 token 登录端点
    
    username 字段可以是学号或邮箱。
    """
    user = await user_crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="学号/邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    
    # 使用 student_id 作为 JWT subject
    access_token = create_access_token(data={"sub": user.student_id})
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    用户注册
    
    必须提供学号，邮箱可选。
    """
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
    
    # 创建新用户
    new_user = await user_crud.create_user(db, user_data, role="user")
    
    return User.model_validate(new_user)

