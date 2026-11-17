from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class HomeStats(BaseModel):
    notes: int
    tags: int
    folders: int
    categories: int
    words: int
    links: int


class HomeRecentNote(BaseModel):
    id: str
    title: str
    excerpt: str = ""
    updated_at: datetime
    folder_id: Optional[str] = None
    category_id: Optional[str] = None
    link_count: int = 0


class HomeRecentRead(BaseModel):
    note_id: str
    title: str
    excerpt: str = ""
    viewed_at: datetime


class HomeTopTag(BaseModel):
    id: str
    name: str
    note_count: int


class HomeArea(BaseModel):
    id: str
    name: str
    note_count: int


class HomeOverview(BaseModel):
    stats: HomeStats
    recent_notes: List[HomeRecentNote]
    recent_reads: List[HomeRecentRead]
    top_tags: List[HomeTopTag]
    areas: List[HomeArea]
