from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class TagBase(BaseModel):
    name: str
    color: Optional[str] = "#00d4ff"

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

class TagResponse(TagBase):
    id: str
    note_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True
