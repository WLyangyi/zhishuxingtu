from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint

from app.db.base import Base, generate_uuid


class NoteView(Base):
    """阅读记录：每个用户对每篇笔记只保留最近一次打开时间。"""

    __tablename__ = "note_views"
    __table_args__ = (
        UniqueConstraint("user_id", "note_id", name="uq_note_views_user_note"),
        Index("ix_note_views_user_time", "user_id", "viewed_at"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    note_id = Column(
        String(36), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    viewed_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
