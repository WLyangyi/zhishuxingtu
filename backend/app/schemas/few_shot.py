from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class FewShotExampleBase(BaseModel):
    prompt_id: Optional[str] = None
    scenario: str
    input_example: str
    output_example: str
    quality_score: float = 5.0

class FewShotExampleCreate(FewShotExampleBase):
    pass

class FewShotExampleUpdate(BaseModel):
    input_example: Optional[str] = None
    output_example: Optional[str] = None
    quality_score: Optional[float] = None
    is_active: Optional[bool] = None

class FewShotExampleInDB(FewShotExampleBase):
    id: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class PromptVersionBase(BaseModel):
    prompt_id: str
    version_number: str
    version_name: Optional[str] = None
    system_prompt: str
    user_prompt_template: Optional[str] = None
    changes_description: Optional[str] = None

class PromptVersionCreate(PromptVersionBase):
    pass

class PromptVersionUpdate(BaseModel):
    version_name: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    changes_description: Optional[str] = None
    is_active: Optional[bool] = None

class PromptVersionInDB(PromptVersionBase):
    id: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ABExperimentBase(BaseModel):
    name: str
    description: Optional[str] = None
    prompt_id: str
    version_a_id: str
    version_b_id: str
    traffic_split: float = 0.5

class ABExperimentCreate(ABExperimentBase):
    pass

class ABExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    traffic_split: Optional[float] = None
    status: Optional[str] = None
    end_time: Optional[datetime] = None

class ABExperimentInDB(ABExperimentBase):
    id: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ABTestResultBase(BaseModel):
    experiment_id: str
    version_id: str
    session_id: Optional[str] = None
    user_question: str
    ai_response: str
    response_time_ms: Optional[int] = None
    token_count: Optional[int] = None
    user_feedback: Optional[int] = None

class ABTestResultCreate(ABTestResultBase):
    pass

class ABTestResultInDB(ABTestResultBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ABExperimentStats(BaseModel):
    experiment_id: str
    experiment_name: Optional[str] = None
    version_a_id: str
    version_b_id: str
    total_samples: int
    version_a_samples: int
    version_b_samples: int
    version_a_avg_feedback: Optional[float]
    version_b_avg_feedback: Optional[float]
    version_a_avg_response_time: Optional[float]
    version_b_avg_response_time: Optional[float]
