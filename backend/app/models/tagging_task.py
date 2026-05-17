"""
Student tagging task models.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class TaggingTask(Base):
    """Batch of photos assigned to one student tagger."""

    __tablename__ = "tagging_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    description = Column(Text)
    creator_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    assignee_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)

    creator = relationship("User", foreign_keys=[creator_id])
    assignee = relationship("User", foreign_keys=[assignee_id])
    items = relationship("TaggingTaskItem", back_populates="task", cascade="all, delete-orphan")


class TaggingTaskItem(Base):
    """Single photo submission within a tagging task."""

    __tablename__ = "tagging_task_items"
    __table_args__ = (
        UniqueConstraint("task_id", "photo_id", name="uq_tagging_task_item_photo"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tagging_tasks.id"), nullable=False, index=True)
    photo_id = Column(String(36), ForeignKey("photos.id"), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False, index=True)
    original_tags = Column(JSON)
    submitted_tags = Column(JSON)
    original_classifications = Column(JSON)
    submitted_classifications = Column(JSON)
    submitter_note = Column(Text)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    reviewer_note = Column(Text)
    submitted_at = Column(DateTime)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    task = relationship("TaggingTask", back_populates="items")
    photo = relationship("Photo")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
