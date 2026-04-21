from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.tag import Tag
from app.models.note import Note
from app.models.user import User
from app.schemas import Response, TagCreate, TagUpdate, TagResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/tags", tags=["标签"])

@router.get("", response_model=Response[List[TagResponse]])
async def get_tags(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tags = db.query(Tag).all()
    result = []
    for tag in tags:
        note_count = db.query(Note).join(Note.tags).filter(Tag.id == tag.id).count()
        result.append(TagResponse(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            note_count=note_count,
            created_at=tag.created_at
        ))
    return Response(data=result)

@router.post("", response_model=Response[TagResponse])
async def create_tag(
    tag_data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = db.query(Tag).filter(Tag.name == tag_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="标签名称已存在")
    
    tag = Tag(
        name=tag_data.name,
        color=tag_data.color
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    
    return Response(data=TagResponse(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        note_count=0,
        created_at=tag.created_at
    ), message="标签创建成功")

@router.put("/{tag_id}", response_model=Response[TagResponse])
async def update_tag(
    tag_id: str,
    tag_data: TagUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    
    if tag_data.name is not None:
        existing = db.query(Tag).filter(Tag.name == tag_data.name, Tag.id != tag_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="标签名称已存在")
        tag.name = tag_data.name
    if tag_data.color is not None:
        tag.color = tag_data.color
    
    db.commit()
    db.refresh(tag)
    
    note_count = db.query(Note).join(Note.tags).filter(Tag.id == tag.id).count()
    
    return Response(data=TagResponse(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        note_count=note_count,
        created_at=tag.created_at
    ), message="标签更新成功")

@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    
    db.delete(tag)
    db.commit()
    return Response(message="标签删除成功")
