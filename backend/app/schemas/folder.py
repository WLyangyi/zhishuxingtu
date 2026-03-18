from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class FolderBase(BaseModel):
    name: str
    parent_id: Optional[str] = None
    category_id: Optional[str] = None

class FolderCreate(FolderBase):
    pass

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[str] = None

class FolderResponse(FolderBase):
    id: str
    level: int
    note_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

class FolderTreeResponse(FolderResponse):
    children: List['FolderTreeResponse'] = []
