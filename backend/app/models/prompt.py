import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, DateTime
from app.db.base import Base

class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    category = Column(String(50), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, default="")
    output_format = Column(Text, default="")
    variables = Column(Text, default="[]")
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    priority = Column(String(20), default="normal")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def variables_list(self):
        if not self.variables:
            return []
        try:
            import json
            return json.loads(self.variables)
        except:
            return []
