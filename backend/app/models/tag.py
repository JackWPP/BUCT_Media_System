"""
标签模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Tag(Base):
    """标签表"""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50))  # object/scene/color/mood
    color = Column(String(7))  # HEX 颜色值
    usage_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    photo_tags = relationship("PhotoTag", back_populates="tag", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tag(name='{self.name}', usage_count={self.usage_count})>"


class PhotoTag(Base):
    """照片标签关联表"""
    __tablename__ = "photo_tags"

    photo_id = Column(String(36), ForeignKey("photos.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    photo = relationship("Photo", back_populates="tags")
    tag = relationship("Tag", back_populates="photo_tags")

    def __repr__(self):
        return f"<PhotoTag(photo_id={self.photo_id}, tag_id={self.tag_id})>"
