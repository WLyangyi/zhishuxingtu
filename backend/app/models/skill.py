import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Skill(Base):
    __tablename__ = "skills"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    icon = Column(String(50), default="⚡")
    color = Column(String(7), default="#00d4ff")
    input_schema = Column(Text, default="{}")
    output_schema = Column(Text, default="{}")
    execution_logic = Column(Text, default="{}")
    trigger_type = Column(String(20), default="manual")
    schedule_config = Column(Text, default="{}")
    output_category_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"))
    output_type_id = Column(String(36), ForeignKey("content_types.id", ondelete="SET NULL"))
    output_tag_ids = Column(Text, default="[]")
    is_template = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    executions = relationship("SkillExecution", back_populates="skill", cascade="all, delete-orphan")

class SkillExecution(Base):
    __tablename__ = "skill_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    skill_id = Column(String(36), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    input_data = Column(Text)
    output_data = Column(Text)
    output_content_id = Column(String(36), ForeignKey("contents.id", ondelete="SET NULL"))
    status = Column(String(20), default="pending")
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    skill = relationship("Skill", back_populates="executions")
