"""
任务模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Task(Base):
    """任务表"""
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="pending", nullable=False)  # pending/in_progress/completed/archived
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)

    # 关系
    creator = relationship("User", back_populates="tasks")
    task_photos = relationship("TaskPhoto", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Task(name='{self.name}', status='{self.status}')>"


class TaskPhoto(Base):
    """任务照片关联表"""
    __tablename__ = "task_photos"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), primary_key=True)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id"), primary_key=True)
    verification_status = Column(String(20), default="unverified", nullable=False)  # unverified/verified/rejected
    verified_at = Column(DateTime)

    # 关系
    task = relationship("Task", back_populates="task_photos")
    photo = relationship("Photo", back_populates="task_photos")

    def __repr__(self):
        return f"<TaskPhoto(task_id={self.task_id}, photo_id={self.photo_id})>"
