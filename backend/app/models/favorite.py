"""
照片收藏模型

用户收藏照片，多对多关系。
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from app.core.database import Base


class Favorite(Base):
    """
    收藏表

    用户与照片的多对多收藏关系。
    """
    __tablename__ = "favorites"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_id = Column(String(36), ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "photo_id", name="uq_user_photo_favorite"),
    )

    def __repr__(self):
        return f"<Favorite(user_id='{self.user_id}', photo_id='{self.photo_id}')>"
