from sqlalchemy import Column, String, ForeignKey, Index
from app.db.base import Base


class NoteLink(Base):
    """双向链接的出边记录：source 持有出链，反链 = target_id 匹配的行。

    JSON 字段 notes.linked_note_ids 暂时保留作为回滚保险，读写两侧同时维护，
    待 P1-1 验收通过后再由一个独立清理提交移除。
    """

    __tablename__ = "note_links"
    __table_args__ = (
        Index("ix_note_links_target", "target_id"),
    )

    source_id = Column(String(36), ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    target_id = Column(String(36), ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
