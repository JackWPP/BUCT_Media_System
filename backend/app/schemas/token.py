"""
Token Pydantic schemas
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
    email: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request schema"""
    email: str
    password: str


class LoginResponse(Token):
    """Login response with user info"""
    user: User
