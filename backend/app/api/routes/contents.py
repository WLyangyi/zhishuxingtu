import json
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.category import Category, ContentType, Content
from app.models.tag import Tag, content_tags
from app.schemas.category import (
    ContentCreate, ContentUpdate, ContentInDB, ContentListResponse
)
from app.schemas import Response

router = APIRouter(prefix="/contents", tags=["contents"])

def parse_linked_content_ids(content_text: str) -> List[str]:
    if not content_text:
        return []
    pattern = r'\[\[([^\]]+)\]\]'
    matches = re.findall(pattern, content_text)
    return matches

def content_to_dict(content: Content) -> dict:
    return {
        "id": content.id,
        "type_id": content.type_id,
        "category_id": content.category_id,
        "user_id": content.user_id,
        "title": content.title,
        "content": content.content,
        "extra_fields": json.loads(content.extra_fields) if content.extra_fields else {},
        "linked_content_ids": json.loads(content.linked_content_ids) if content.linked_content_ids else [],
        "file_path": content.file_path,
        "file_url": content.file_url,
        "file_size": content.file_size or 0,
        "created_at": content.created_at,
        "updated_at": content.updated_at,
        "content_type": {
            "id": content.content_type.id,
            "name": content.content_type.name,
            "icon": content.content_type.icon,
            "color": content.content_type.color,
            "field_schema": json.loads(content.content_type.field_schema) if content.content_type.field_schema else {}
        } if content.content_type else None,
        "category": {
            "id": content.category.id,
            "name": content.category.name,
            "icon": content.category.icon,
            "color": content.category.color,
            "sort_order": content.category.sort_order,
            "is_system": content.category.is_system,
            "created_at": content.category.created_at,
            "content_types": []
        } if content.category else None,
        "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in content.tags]
    }

@router.get("", response_model=Response[ContentListResponse])
async def get_contents(
    category_id: Optional[str] = Query(None),
    type_id: Optional[str] = Query(None),
    tag_id: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Content).filter(Content.user_id == current_user.id)
    
    if category_id:
        query = query.filter(Content.category_id == category_id)
    
    if type_id:
        query = query.filter(Content.type_id == type_id)
    
    if tag_id:
        query = query.join(content_tags).filter(content_tags.c.tag_id == tag_id)
    
    if keyword:
        query = query.filter(
            Content.title.contains(keyword) | Content.content.contains(keyword)
        )
    
    total = query.count()
    items = query.order_by(Content.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return Response(data=ContentListResponse(
        items=[content_to_dict(item) for item in items],
        total=total,
        page=page,
        page_size=page_size
    ))

@router.get("/{content_id}", response_model=Response[ContentInDB])
async def get_content(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    return Response(data=content_to_dict(content))

@router.post("", response_model=Response[ContentInDB])
async def create_content(
    data: ContentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content_type = db.query(ContentType).filter(ContentType.id == data.type_id).first()
    if not content_type:
        raise HTTPException(status_code=400, detail="内容类型不存在")
    
    category = db.query(Category).filter(Category.id == data.category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="分类不存在")
    
    linked_titles = parse_linked_content_ids(data.content or "")
    linked_ids = []
    for title in linked_titles:
        linked_content = db.query(Content).filter(
            Content.title == title,
            Content.user_id == current_user.id
        ).first()
        if linked_content:
            linked_ids.append(linked_content.id)
    
    content = Content(
        type_id=data.type_id,
        category_id=data.category_id,
        user_id=current_user.id,
        title=data.title,
        content=data.content,
        extra_fields=json.dumps(data.extra_fields) if data.extra_fields else "{}",
        linked_content_ids=json.dumps(linked_ids)
    )
    db.add(content)
    db.flush()
    
    if data.tag_ids:
        for tag_id in data.tag_ids:
            tag = db.query(Tag).filter(Tag.id == tag_id).first()
            if tag:
                content.tags.append(tag)
    
    db.commit()
    db.refresh(content)
    
    return Response(data=content_to_dict(content), message="内容创建成功")

@router.put("/{content_id}", response_model=Response[ContentInDB])
async def update_content(
    content_id: str,
    data: ContentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    
    if "tag_ids" in update_data:
        tag_ids = update_data.pop("tag_ids")
        content.tags = []
        if tag_ids:
            for tag_id in tag_ids:
                tag = db.query(Tag).filter(Tag.id == tag_id).first()
                if tag:
                    content.tags.append(tag)
    
    if "extra_fields" in update_data and update_data["extra_fields"] is not None:
        update_data["extra_fields"] = json.dumps(update_data["extra_fields"])
    
    if data.content is not None:
        linked_titles = parse_linked_content_ids(data.content)
        linked_ids = []
        for title in linked_titles:
            linked_content = db.query(Content).filter(
                Content.title == title,
                Content.user_id == current_user.id
            ).first()
            if linked_content:
                linked_ids.append(linked_content.id)
        update_data["linked_content_ids"] = json.dumps(linked_ids)
    
    for key, value in update_data.items():
        setattr(content, key, value)
    
    db.commit()
    db.refresh(content)
    
    return Response(data=content_to_dict(content), message="内容更新成功")

@router.delete("/{content_id}")
async def delete_content(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    db.delete(content)
    db.commit()
    
    return Response(message="内容已删除")

@router.get("/{content_id}/backlinks")
async def get_content_backlinks(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    backlinks = db.query(Content).filter(
        Content.linked_content_ids.contains(f'"{content_id}"'),
        Content.user_id == current_user.id
    ).all()
    
    return Response(data={
        "items": [{"id": c.id, "title": c.title} for c in backlinks],
        "total": len(backlinks)
    })
