import json
import re
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models.note import Note
from app.models.note_link import NoteLink
from app.models.tag import Tag
from app.models.user import User
from app.schemas import Response, NoteCreate, NoteUpdate, NoteResponse, NoteListResponse, BacklinkResponse
from app.api.deps import get_current_user
from app.queries.home import record_note_view
from app.queries.note_links import (
    add_outgoing_links,
    outgoing_links_by_source,
    replace_outgoing_links,
)
from app.services import get_vector_store
from app.services.vector_store_adapter import get_vector_store_adapter
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

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
        query = query.filter(Note.folder_id.in_(folder_ids))
    
    total = query.count()
    notes = query.order_by(Note.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    links_by_source = outgoing_links_by_source(db, [note.id for note in notes])
    items = []
    for note in notes:
        note_dict = {
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "folder_id": note.folder_id,
            "linked_note_ids": links_by_source.get(note.id, []),
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
        except (json_module.JSONDecodeError, ValueError):
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

    # P1-1: JSON 字段保留作回滚保险，关联表是反链/图谱的索引查询入口。
    add_outgoing_links(db, note.id, linked_ids)
    db.commit()

    vector_store = get_vector_store_adapter()
    if vector_store and embedding_service.available and note.content:
        try:
            chunks, vectors = embedding_service.embed_chunks(note.id, note.title, note.content)
            if chunks and len(vectors) > 0:
                vector_store.add_note_chunks(note.id, chunks, vectors)
        except Exception as e:
            logger.warning(f"Failed to add vector for note {note.id}: {e}")
    
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
        "linked_note_ids": outgoing_links_by_source(db, [note.id]).get(note.id, []),
        "tags": note_tags,
        "created_at": note.created_at,
        "updated_at": note.updated_at
    }
    return Response(data=note_dict)

@router.post("/{note_id}/view", status_code=204)
async def record_view(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """记录当前用户打开过该笔记（按 user+note 幂等 upsert）。"""
    try:
        record_note_view(db, current_user.id, note_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="笔记不存在")

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
        linked_ids = resolve_links(db, note_data.content)
        note.linked_note_ids = json.dumps(linked_ids)
        replace_outgoing_links(db, note.id, linked_ids)
    
    if hasattr(note_data, 'folder_id') and note_data.folder_id is not None:
        note.folder_id = note_data.folder_id if note_data.folder_id else None
    
    if note_data.tag_ids is not None:
        tags = db.query(Tag).filter(Tag.id.in_(note_data.tag_ids)).all()
        note.tags = tags
    
    db.commit()
    db.refresh(note)

    vector_store = get_vector_store_adapter()
    if vector_store and embedding_service.available and note.content:
        try:
            chunks, vectors = embedding_service.embed_chunks(note.id, note.title, note.content)
            if chunks and len(vectors) > 0:
                vector_store.add_note_chunks(note.id, chunks, vectors)
        except Exception as e:
            print(f"Failed to update vector for note {note.id}: {e}")
    
    note_tags = [{"id": t.id, "name": t.name, "color": t.color} for t in note.tags]
    note_dict = {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "folder_id": note.folder_id,
        "linked_note_ids": outgoing_links_by_source(db, [note.id]).get(note.id, []),
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
    
    vector_store = get_vector_store()
    vector_store_adapter = get_vector_store_adapter()
    if vector_store:
        try:
            vector_store.remove_vector(note_id)
            vector_store_adapter.clear()
        except Exception as e:
            print(f"Failed to remove vector for note {note_id}: {e}")
    
    # 删除来源笔记要清出边，删除目标笔记要清反链，避免关联表留下悬空 id
    db.query(NoteLink).filter(
        (NoteLink.source_id == note_id) | (NoteLink.target_id == note_id)
    ).delete(synchronize_session=False)
    db.delete(note)
    db.commit()
    return Response(message="笔记删除成功")

@router.get("/{note_id}/backlinks", response_model=Response[list])
async def get_backlinks(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    backlink_notes = (
        db.query(Note)
        .join(NoteLink, NoteLink.source_id == Note.id)
        .filter(NoteLink.target_id == note_id, Note.user_id == current_user.id)
        .all()
    )
    
    backlinks = []
    for note in backlink_notes:
        backlinks.append(BacklinkResponse(
            id=note.id,
            title=note.title,
            created_at=note.created_at
        ))
    
    return Response(data=backlinks)


@router.get("/{note_id}/unlinked-mentions", response_model=Response[list])
async def get_unlinked_mentions(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """P2-4:后端预计算未链接提及——正文中以纯文本出现、但未写成 [[ ]] 的同用户笔记。

    排除 [[...]] 锚文本、当前笔记自身与其它用户的笔记；按正文首次出现顺序返回。
    前端可在编辑期继续用本地纯函数做实时提示，此接口提供服务端权威结果（供 MCP 等消费）。
    """
    note = db.query(Note).filter(
        Note.id == note_id, Note.user_id == current_user.id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    content = note.content or ""
    plain = LINK_PATTERN.sub("", content)
    lower = plain.lower()

    candidates = (
        db.query(Note)
        .filter(Note.user_id == current_user.id, Note.id != note_id)
        .all()
    )

    hits = []
    for candidate in candidates:
        title = (candidate.title or "").strip()
        if not title:
            continue
        at = lower.find(title.lower())
        if at >= 0:
            hits.append((at, {"id": candidate.id, "title": candidate.title}))
    hits.sort(key=lambda item: item[0])

    return Response(data=[item for _, item in hits])
