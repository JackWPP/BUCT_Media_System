"""
Taxonomy models for controlled gallery classifications.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class TaxonomyFacet(Base):
    """Classification facet such as season, campus, building, or gallery year."""

    __tablename__ = "taxonomy_facets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    selection_mode = Column(String(20), default="single", nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    nodes = relationship(
        "TaxonomyNode",
        back_populates="facet",
        cascade="all, delete-orphan",
        order_by="TaxonomyNode.sort_order",
    )
    photo_classifications = relationship(
        "PhotoClassification",
        back_populates="facet",
        cascade="all, delete-orphan",
    )


class TaxonomyNode(Base):
    """Concrete selectable taxonomy node."""

    __tablename__ = "taxonomy_nodes"
    __table_args__ = (
        UniqueConstraint("facet_id", "key", name="uq_taxonomy_node_facet_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    facet_id = Column(Integer, ForeignKey("taxonomy_facets.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("taxonomy_nodes.id"), nullable=True, index=True)
    key = Column(String(100), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    facet = relationship("TaxonomyFacet", back_populates="nodes")
    parent = relationship("TaxonomyNode", remote_side=[id], back_populates="children")
    children = relationship(
        "TaxonomyNode",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="TaxonomyNode.sort_order",
    )
    aliases = relationship(
        "TaxonomyAlias",
        back_populates="node",
        cascade="all, delete-orphan",
    )
    photo_classifications = relationship(
        "PhotoClassification",
        back_populates="node",
        cascade="all, delete-orphan",
    )


class TaxonomyAlias(Base):
    """Alias mapping for taxonomy nodes."""

    __tablename__ = "taxonomy_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(Integer, ForeignKey("taxonomy_nodes.id"), nullable=False, index=True)
    alias = Column(String(150), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    node = relationship("TaxonomyNode", back_populates="aliases")


class PhotoClassification(Base):
    """Single selected taxonomy node for a photo facet."""

    __tablename__ = "photo_classifications"
    __table_args__ = (
        UniqueConstraint("photo_id", "facet_id", name="uq_photo_classification_photo_facet"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    photo_id = Column(String(36), ForeignKey("photos.id"), nullable=False, index=True)
    facet_id = Column(Integer, ForeignKey("taxonomy_facets.id"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("taxonomy_nodes.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    photo = relationship("Photo", back_populates="classifications")
    facet = relationship("TaxonomyFacet", back_populates="photo_classifications")
    node = relationship("TaxonomyNode", back_populates="photo_classifications")
