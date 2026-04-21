import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.db.base import Base

class FewShotExample(Base):
    __tablename__ = "few_shot_examples"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt_id = Column(String(36), ForeignKey("prompts.id"), nullable=True)
    scenario = Column(String(50), nullable=False)
    input_example = Column(Text, nullable=False)
    output_example = Column(Text, nullable=False)
    quality_score = Column(Float, default=5.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    prompt = relationship("Prompt", back_populates="few_shot_examples")

class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt_id = Column(String(36), ForeignKey("prompts.id"), nullable=False)
    version_number = Column(String(20), nullable=False)
    version_name = Column(String(100))
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text)
    changes_description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    prompt = relationship("Prompt", back_populates="versions")

class ABExperiment(Base):
    __tablename__ = "ab_experiments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    prompt_id = Column(String(36), ForeignKey("prompts.id"), nullable=False)
    version_a_id = Column(String(36), ForeignKey("prompt_versions.id"), nullable=False)
    version_b_id = Column(String(36), ForeignKey("prompt_versions.id"), nullable=False)
    traffic_split = Column(Float, default=0.5)
    status = Column(String(20), default="running")
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    prompt = relationship("Prompt", back_populates="experiments")
    version_a = relationship("PromptVersion", foreign_keys=[version_a_id])
    version_b = relationship("PromptVersion", foreign_keys=[version_b_id])
    results = relationship("ABTestResult", back_populates="experiment")

class ABTestResult(Base):
    __tablename__ = "ab_test_results"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String(36), ForeignKey("ab_experiments.id"), nullable=False)
    version_id = Column(String(36), ForeignKey("prompt_versions.id"), nullable=False)
    session_id = Column(String(36))
    user_question = Column(Text)
    ai_response = Column(Text)
    response_time_ms = Column(String(20))
    token_count = Column(String(20))
    user_feedback = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    experiment = relationship("ABExperiment", back_populates="results")
    version = relationship("PromptVersion")

class PromptChain(Base):
    __tablename__ = "prompt_chains"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    steps = relationship("ChainStep", back_populates="chain", order_by="ChainStep.step_order")
    executions = relationship("ChainExecution", back_populates="chain")

class ChainStep(Base):
    __tablename__ = "chain_steps"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chain_id = Column(String(36), ForeignKey("prompt_chains.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    step_name = Column(String(100), nullable=False)
    prompt_template = Column(Text, nullable=False)
    input_mapping = Column(Text)
    output_mapping = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chain = relationship("PromptChain", back_populates="steps")

class ChainExecution(Base):
    __tablename__ = "chain_executions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chain_id = Column(String(36), ForeignKey("prompt_chains.id"), nullable=False)
    session_id = Column(String(36))
    input_data = Column(Text)
    output_data = Column(Text)
    status = Column(String(20), default="pending")
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    chain = relationship("PromptChain", back_populates="executions")

class PromptEvaluation(Base):
    __tablename__ = "prompt_evaluations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt_version_id = Column(String(36), ForeignKey("prompt_versions.id"), nullable=True)
    session_id = Column(String(36))
    question = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    context = Column(Text)
    
    relevance_score = Column(Float)
    accuracy_score = Column(Float)
    completeness_score = Column(Float)
    clarity_score = Column(Float)
    overall_score = Column(Float)
    
    response_time_ms = Column(String(20))
    token_count = Column(String(20))
    cost_usd = Column(Float, default=0.0)
    
    user_rating = Column(String(10))
    user_feedback = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    version = relationship("PromptVersion")
