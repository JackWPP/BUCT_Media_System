"""
Token Pydantic schemas

支持学号/邮箱登录。
"""
from typing import Optional
from pydantic import BaseModel
from app.schemas.user import User


class Token(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload schema"""
    sub: Optional[str] = None  # 学号或邮箱


class LoginRequest(BaseModel):
    """
    Login request schema
    
    identifier: 学号或邮箱，作为登录凭证
    """
    identifier: str  # 学号或邮箱
    password: str


class LoginResponse(Token):
    """Login response with user info"""
    user: User

