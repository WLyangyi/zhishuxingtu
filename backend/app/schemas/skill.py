from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class SkillBase(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = "⚡"
    color: Optional[str] = "#00d4ff"
    input_schema: Optional[Dict[str, Any]] = {}
    output_schema: Optional[Dict[str, Any]] = {}
    execution_logic: Optional[Dict[str, Any]] = {}
    trigger_type: Optional[str] = "manual"
    schedule_config: Optional[Dict[str, Any]] = {}
    output_category_id: Optional[str] = None
    output_type_id: Optional[str] = None
    output_tag_ids: Optional[List[str]] = []

class SkillCreate(SkillBase):
    pass

class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    execution_logic: Optional[Dict[str, Any]] = None
    trigger_type: Optional[str] = None
    schedule_config: Optional[Dict[str, Any]] = None
    output_category_id: Optional[str] = None
    output_type_id: Optional[str] = None
    output_tag_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None

class SkillExecutionBase(BaseModel):
    input_data: Optional[Dict[str, Any]] = None

class SkillExecutionCreate(SkillExecutionBase):
    pass

class SkillExecutionInDB(BaseModel):
    id: str
    skill_id: str
    user_id: str
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    output_content_id: Optional[str]
    status: str
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class SkillInDB(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    icon: str
    color: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    execution_logic: Dict[str, Any]
    trigger_type: str
    schedule_config: Dict[str, Any]
    output_category_id: Optional[str]
    output_type_id: Optional[str]
    output_tag_ids: List[str]
    is_template: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SkillListResponse(BaseModel):
    items: List[SkillInDB]
    total: int

class SkillTemplate(BaseModel):
    name: str
    description: str
    icon: str
    color: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    execution_logic: Dict[str, Any]
    trigger_type: str
