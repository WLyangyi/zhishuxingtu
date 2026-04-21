from sqlalchemy import Column, String, Integer, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, generate_uuid

class Folder(Base, TimestampMixin):
    __tablename__ = "folders"
    __table_args__ = (
        CheckConstraint('level IN (0, 1, 2, 3)', name='check_folder_level'),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    parent_id = Column(String(36), ForeignKey("folders.id"), nullable=True)
    level = Column(Integer, nullable=False, default=0)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)

    parent = relationship("Folder", remote_side=[id], backref="children")
    category = relationship("Category", backref="folders")
    notes = relationship("Note", back_populates="folder")
