"""
用户模型

支持学号 (student_id) 作为主要身份标识，为对接学校统一身份认证做准备。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    """
    用户表
    
    Attributes:
        student_id: 学号/工号，作为核心身份标识，唯一且有索引
        email: 邮箱，保留作为备用登录方式
        role: 角色 (admin/auditor/dept_user/user)
    """
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(20), unique=True, index=True, nullable=False, comment="学号/工号，核心身份标识")
    email = Column(String(255), unique=True, nullable=True, index=True, comment="邮箱，可选")
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), default="user", nullable=False)  # admin/auditor/dept_user/user
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    photos = relationship("Photo", back_populates="uploader", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="creator", cascade="all, delete-orphan")
    permissions = relationship("ResourcePermission", back_populates="user", cascade="all, delete-orphan", foreign_keys="ResourcePermission.user_id")

    def __repr__(self):
        return f"<User(student_id='{self.student_id}', email='{self.email}', role='{self.role}')>"

