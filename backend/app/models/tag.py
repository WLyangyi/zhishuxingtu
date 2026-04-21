from sqlalchemy import Column, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, generate_uuid
from app.models.note import note_tags

content_tags = Table(
    'content_tags',
    Base.metadata,
    Column('content_id', String(36), ForeignKey('contents.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', String(36), ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

class Tag(Base, TimestampMixin):
    __tablename__ = "tags"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)
    color = Column(String(7), default="#00d4ff")
    
    notes = relationship("Note", secondary=note_tags, back_populates="tags")
    contents = relationship("Content", secondary=content_tags, back_populates="tags")
