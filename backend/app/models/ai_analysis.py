"""
AI analysis task models.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class AIAnalysisTask(Base):
    """Persisted AI analysis job and suggestion payload."""

    __tablename__ = "ai_analysis_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    photo_id = Column(String(36), ForeignKey("photos.id"), nullable=False, index=True)
    requested_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    provider = Column(String(50), nullable=False)
    model_id = Column(String(100), nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending/processing/completed/failed/applied/ignored
    prompt_version = Column(String(20), default="v2", nullable=False)
    result_json = Column(JSON)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    applied_at = Column(DateTime)

    photo = relationship("Photo", back_populates="ai_analysis_tasks")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
