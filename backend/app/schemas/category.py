from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
import json

class CategoryBase(BaseModel):
    name: str
    icon: Optional[str] = "📁"
    color: Optional[str] = "#00d4ff"
    sort_order: Optional[int] = 0

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None

class ContentTypeInDB(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    field_schema: dict = {}

    @field_validator('field_schema', mode='before')
    @classmethod
    def parse_field_schema(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return {}
        return v if isinstance(v, dict) else {}

    class Config:
        from_attributes = True

class CategoryInDB(CategoryBase):
    id: str
    is_system: bool
    created_at: datetime
    content_types: List[ContentTypeInDB] = []

    class Config:
        from_attributes = True

class ContentTypeBase(BaseModel):
    name: str
    category_id: str
    icon: Optional[str] = "📝"
    color: Optional[str] = "#00d4ff"
    field_schema: Optional[dict] = {}

class ContentTypeCreate(ContentTypeBase):
    pass

class ContentTypeUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    field_schema: Optional[dict] = None

class ContentTagInDB(BaseModel):
    id: str
    name: str
    color: str

    class Config:
        from_attributes = True

class ContentBase(BaseModel):
    title: str
    content: Optional[str] = None
    type_id: str
    category_id: str
    extra_fields: Optional[dict] = {}
    tag_ids: Optional[List[str]] = []

class ContentCreate(ContentBase):
    pass

class ContentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    type_id: Optional[str] = None
    category_id: Optional[str] = None
    extra_fields: Optional[dict] = None
    tag_ids: Optional[List[str]] = None
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None

class ContentInDB(BaseModel):
    id: str
    type_id: str
    category_id: str
    user_id: str
    title: str
    content: Optional[str]
    extra_fields: dict
    linked_content_ids: List[str]
    file_path: Optional[str]
    file_url: Optional[str]
    file_size: int
    created_at: datetime
    updated_at: datetime
    content_type: Optional[ContentTypeInDB] = None
    category: Optional[CategoryInDB] = None
    tags: List[ContentTagInDB] = []

    class Config:
        from_attributes = True

class ContentListResponse(BaseModel):
    items: List[ContentInDB]
    total: int
    page: int
    page_size: int
