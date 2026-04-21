import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    icon = Column(String(50), default="📁")
    color = Column(String(7), default="#00d4ff")
    sort_order = Column(Integer, default=0)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    content_types = relationship("ContentType", back_populates="category", cascade="all, delete-orphan")
    contents = relationship("Content", back_populates="category", cascade="all, delete-orphan")

class ContentType(Base):
    __tablename__ = "content_types"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    icon = Column(String(50), default="📝")
    color = Column(String(7), default="#00d4ff")
    field_schema = Column(Text, default="{}")
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="content_types")
    contents = relationship("Content", back_populates="content_type", cascade="all, delete-orphan")

class Content(Base):
    __tablename__ = "contents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type_id = Column(String(36), ForeignKey("content_types.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    extra_fields = Column(Text, default="{}")
    linked_content_ids = Column(Text, default="[]")
    file_path = Column(String(500))
    file_url = Column(String(1000))
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    content_type = relationship("ContentType", back_populates="contents")
    category = relationship("Category", back_populates="contents")
    tags = relationship("Tag", secondary="content_tags", back_populates="contents", viewonly=True)
