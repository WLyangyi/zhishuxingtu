from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint

from app.db.base import Base, TimestampMixin, generate_uuid


class ImportVisualAsset(Base, TimestampMixin):
    __tablename__ = "import_visual_assets"
    __table_args__ = (
        UniqueConstraint("note_id", "page_number", name="uq_import_visual_note_page"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    note_id = Column(String(36), ForeignKey("notes.id"), nullable=False, index=True)
    task_id = Column(String(36), nullable=True)
    page_number = Column(Integer, nullable=False)
    image_path = Column(String(1000), nullable=False)
    mime_type = Column(String(50), nullable=False, default="image/png")
    sha256 = Column(String(64), nullable=False)
    source_filename = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    description_status = Column(String(20), nullable=False, default="pending")
    model = Column(String(100), nullable=True)
    prompt_version = Column(String(50), nullable=True)
