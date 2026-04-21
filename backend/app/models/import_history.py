from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from app.db.base import Base, TimestampMixin, generate_uuid


class ImportHistory(Base, TimestampMixin):
    __tablename__ = "import_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    task_id = Column(String(36), nullable=False)
    source_type = Column(String(20), nullable=False)
    source_url = Column(String(1000), nullable=True)
    source_filename = Column(String(500), nullable=True)
    duration = Column(Integer, nullable=True)
    platform = Column(String(50), nullable=True)
    generated_title = Column(String(500), nullable=True)
    note_id = Column(String(36), nullable=True)
    status = Column(String(20), nullable=False, default="completed")
