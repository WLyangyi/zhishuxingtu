from sqlalchemy import Column, String, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, generate_uuid

note_tags = Table(
    'note_tags',
    Base.metadata,
    Column('note_id', String(36), ForeignKey('notes.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', String(36), ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

class Note(Base, TimestampMixin):
    __tablename__ = "notes"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    folder_id = Column(String(36), ForeignKey("folders.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    linked_note_ids = Column(Text, nullable=True)
    
    folder = relationship("Folder", back_populates="notes")
    tags = relationship("Tag", secondary=note_tags, back_populates="notes")
    user = relationship("User", back_populates="notes")
