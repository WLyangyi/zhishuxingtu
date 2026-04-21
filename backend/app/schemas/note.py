from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class NoteBase(BaseModel):
    title: str
    content: Optional[str] = None
    folder_id: Optional[str] = None

class NoteCreate(NoteBase):
    tag_ids: Optional[List[str]] = None

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    folder_id: Optional[str] = None
    tag_ids: Optional[List[str]] = None

class TagBrief(BaseModel):
    id: str
    name: str
    color: str
    
    class Config:
        from_attributes = True

class NoteResponse(NoteBase):
    id: str
    linked_note_ids: Optional[List[str]] = []
    tags: List[TagBrief] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class NoteListResponse(BaseModel):
    items: List[NoteResponse]
    total: int
    page: int
    page_size: int

class BacklinkResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    
    class Config:
        from_attributes = True
