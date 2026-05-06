import uuid
from sqlalchemy import Column, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin

class Prompt(Base, TimestampMixin):
    __tablename__ = "prompts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
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
    
    few_shot_examples = relationship("FewShotExample", back_populates="prompt")
    versions = relationship("PromptVersion", back_populates="prompt")
    experiments = relationship("ABExperiment", back_populates="prompt")

    @property
    def variables_list(self):
        if not self.variables:
            return []
        try:
            import json
            return json.loads(self.variables)
        except (json.JSONDecodeError, ValueError):
            return []
