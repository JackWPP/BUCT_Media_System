"""
User Pydantic schemas

用户相关的数据传输对象定义。
支持 student_id (学号/工号) 作为核心身份标识。
"""
from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, EmailStr, field_validator


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("密码至少8位")
    if not any(c.islower() for c in password):
        raise ValueError("密码需包含小写字母")
    if not any(c.isupper() for c in password):
        raise ValueError("密码需包含大写字母")
    if not any(c.isdigit() for c in password):
        raise ValueError("密码需包含数字")
    return password


class RoleEnum(str, Enum):
    """
    用户角色枚举
    
    - admin: 超级管理员，拥有所有权限
    - auditor: 审核员，可审核照片和编辑标签
    - dept_user: 部门用户，预留扩展
    - user: 普通用户
    """
    ADMIN = "admin"
    AUDITOR = "auditor"
    DEPT_USER = "dept_user"
    USER = "user"


class UserBase(BaseModel):
    """Base user schema"""
    student_id: str  # 学号/工号，核心身份标识，必填
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """用户注册 schema (公开注册)"""
    password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserCreateByAdmin(UserBase):
    """
    管理员创建用户 schema
    
    允许管理员在创建用户时指定角色和学号。
    student_id 为必填字段。
    """
    password: str
    role: RoleEnum = RoleEnum.USER

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    """用户自我更新 schema"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


class UserUpdateByAdmin(BaseModel):
    """
    管理员更新用户 schema
    
    允许管理员修改用户的激活状态、角色和学号。
    """
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[RoleEnum] = None
    student_id: Optional[str] = None


class UserRoleUpdate(BaseModel):
    """
    管理员修改用户角色 schema
    """
    role: RoleEnum


class UserInDB(UserBase):
    """User in database schema"""
    id: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    login_count: int = 0
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    token_version: int = 1
    email_verified: bool = False

    class Config:
        from_attributes = True


class User(UserInDB):
    """User response schema"""
    pass


class UserList(BaseModel):
    """用户列表响应 schema"""
    users: list[User]
    total: int


class PasswordChange(BaseModel):
    """用户自助修改密码"""
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class AdminPasswordReset(BaseModel):
    """管理员重置用户密码"""
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)
