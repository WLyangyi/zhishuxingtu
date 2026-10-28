from sqlalchemy import Column, String, Text, ForeignKey, Table, Index
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
    # 幂等键:写工具按 session + tool_call 派生,唯一索引挡住重放时的第二次落库。
    # SQLite 里多行 NULL 不参与唯一约束,普通笔记(idempotency_key 为 NULL)不受影响。
    __table_args__ = (
        Index("uq_notes_user_idempotency", "user_id", "idempotency_key", unique=True),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    folder_id = Column(String(36), ForeignKey("folders.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    linked_note_ids = Column(Text, nullable=True)
    idempotency_key = Column(String(200), nullable=True)
    
    folder = relationship("Folder", back_populates="notes")
    tags = relationship("Tag", secondary=note_tags, back_populates="notes")
    user = relationship("User", back_populates="notes")
