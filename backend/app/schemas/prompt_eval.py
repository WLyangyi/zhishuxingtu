from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PromptEvaluationBase(BaseModel):
    prompt_version_id: Optional[str] = None
    session_id: Optional[str] = None
    question: str
    response: str
    context: Optional[str] = None
    relevance_score: Optional[float] = None
    accuracy_score: Optional[float] = None
    completeness_score: Optional[float] = None
    clarity_score: Optional[float] = None
    overall_score: Optional[float] = None
    response_time_ms: Optional[int] = None
    token_count: Optional[int] = None
    cost_usd: Optional[float] = None

class PromptEvaluationCreate(PromptEvaluationBase):
    pass

class PromptEvaluationInDB(PromptEvaluationBase):
    id: str
    user_rating: Optional[str] = None
    user_feedback: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class PromptEvaluationStats(BaseModel):
    total_evaluations: int
    avg_overall_score: Optional[float]
    avg_relevance_score: Optional[float]
    avg_accuracy_score: Optional[float]
    avg_completeness_score: Optional[float]
    avg_clarity_score: Optional[float]

class PromptEvaluationWithAuto(BaseModel):
    question: str
    response: str
    context: Optional[str] = None
    session_id: Optional[str] = None
