import json
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models.note import Note
from app.models.tag import Tag
from app.models.user import User
from app.schemas import Response, NoteCreate, NoteUpdate, NoteResponse, NoteListResponse, BacklinkResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/notes", tags=["笔记"])

LINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')

def parse_links(content: str) -> list:
    if not content:
        return []
    matches = LINK_PATTERN.findall(content)
    return [title.strip() for title in matches]

def resolve_links(db: Session, content: str) -> list:
    try:
        titles = parse_links(content)
        linked_ids = []
        for title in titles:
            note = db.query(Note).filter(Note.title == title).first()
            if note:
                linked_ids.append(note.id)
        return linked_ids
    except Exception as e:
        print(f"Error resolving links: {e}")
        return []

@router.get("", response_model=Response[NoteListResponse])
async def list_notes(
    folder_id: Optional[str] = None,
    tag_id: Optional[str] = None,
    category_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Note)
    
    if folder_id:
        query = query.filter(Note.folder_id == folder_id)
    if tag_id:
        query = query.join(Note.tags).filter(Tag.id == tag_id)
    if category_id:
        from app.models.folder import Folder
        folder_ids = [f.id for f in db.query(Folder).filter(Folder.category_id == category_id).all()]
        query = query.filter(Note.folder_id.in_(folder_ids) | Note.folder_id.is_(None))
    
    total = query.count()
    notes = query.order_by(Note.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    items = []
    for note in notes:
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

@router.post("", response_model=Response[NoteResponse])
async def create_note(
    note_data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print(f"Creating note: {note_data.title}, user: {current_user.username}")
    linked_ids = resolve_links(db, note_data.content)
    print(f"Resolved links: {linked_ids}")
    
    tag_ids = note_data.tag_ids
    if isinstance(tag_ids, str):
        import json as json_module
        try:
            tag_ids = json_module.loads(tag_ids)
        except:
            tag_ids = []
    if not isinstance(tag_ids, list):
        tag_ids = []
    
    note = Note(
        title=note_data.title,
        content=note_data.content,
        folder_id=note_data.folder_id,
        user_id=current_user.id,
        linked_note_ids=json.dumps(linked_ids)
    )
    
    if tag_ids:
        tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
        note.tags = tags
    
    db.add(note)
    db.commit()
    db.refresh(note)
    
    note_dict = {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "folder_id": note.folder_id,
        "linked_note_ids": linked_ids,
        "tags": [],
        "created_at": note.created_at,
        "updated_at": note.updated_at
    }
    return Response(data=note_dict, message="笔记创建成功")

@router.get("/{note_id}", response_model=Response[NoteResponse])
async def get_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    note_tags = [{"id": t.id, "name": t.name, "color": t.color} for t in note.tags]
    note_dict = {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "folder_id": note.folder_id,
        "linked_note_ids": json.loads(note.linked_note_ids) if note.linked_note_ids else [],
        "tags": note_tags,
        "created_at": note.created_at,
        "updated_at": note.updated_at
    }
    return Response(data=note_dict)

@router.put("/{note_id}", response_model=Response[NoteResponse])
async def update_note(
    note_id: str,
    note_data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    if note_data.title is not None:
        note.title = note_data.title
    if note_data.content is not None:
        note.content = note_data.content
        note.linked_note_ids = json.dumps(resolve_links(db, note_data.content))
    
    if hasattr(note_data, 'folder_id') and note_data.folder_id is not None:
        note.folder_id = note_data.folder_id if note_data.folder_id else None
    
    if note_data.tag_ids is not None:
        tags = db.query(Tag).filter(Tag.id.in_(note_data.tag_ids)).all()
        note.tags = tags
    
    db.commit()
    db.refresh(note)
    
    note_tags = [{"id": t.id, "name": t.name, "color": t.color} for t in note.tags]
    note_dict = {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "folder_id": note.folder_id,
        "linked_note_ids": json.loads(note.linked_note_ids) if note.linked_note_ids else [],
        "tags": note_tags,
        "created_at": note.created_at,
        "updated_at": note.updated_at
    }
    return Response(data=note_dict, message="笔记更新成功")

@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    db.delete(note)
    db.commit()
    return Response(message="笔记删除成功")

@router.get("/{note_id}/backlinks", response_model=Response[list])
async def get_backlinks(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notes = db.query(Note).all()
    backlinks = []
    
    for note in notes:
        if note.linked_note_ids:
            linked_ids = json.loads(note.linked_note_ids)
            if note_id in linked_ids:
                backlinks.append(BacklinkResponse(
                    id=note.id,
                    title=note.title,
                    created_at=note.created_at
                ))
    
    return Response(data=backlinks)
