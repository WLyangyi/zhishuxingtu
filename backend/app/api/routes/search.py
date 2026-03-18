import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models.note import Note
from app.models.folder import Folder
from app.models.tag import Tag
from app.models.user import User
from app.schemas import Response, NoteResponse, NoteListResponse, GraphResponse, GraphNode, GraphEdge
from app.api.deps import get_current_user

router = APIRouter(prefix="/search", tags=["搜索"])

@router.get("", response_model=Response[NoteListResponse])
async def search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notes = db.query(Note).filter(
        (Note.title.contains(q)) | (Note.content.contains(q))
    ).order_by(Note.updated_at.desc()).all()
    
    total = len(notes)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = notes[start:end]
    
    items = []
    for note in paginated:
        note_dict = {
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "folder_id": note.folder_id,
            "linked_note_ids": json.loads(note.linked_note_ids) if note.linked_note_ids else [],
            "tags": [],
            "created_at": note.created_at,
            "updated_at": note.updated_at
        }
        items.append(note_dict)
    
    return Response(data=NoteListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    ))

@router.post("/ai")
async def ai_search(
    question: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notes = db.query(Note).filter(
        (Note.title.contains(question)) | (Note.content.contains(question))
    ).limit(5).all()
    
    context = "\n\n".join([f"标题: {n.title}\n内容: {n.content or ''}" for n in notes])
    
    return Response(data={
        "answer": f"基于知识库的搜索结果，找到 {len(notes)} 条相关笔记。",
        "context": context,
        "notes": [{"id": n.id, "title": n.title} for n in notes]
    })
