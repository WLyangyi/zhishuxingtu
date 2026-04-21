import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.category import Category, ContentType, Content
from app.models.tag import Tag
from app.schemas import Response
from app.schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryInDB,
    ContentTypeCreate, ContentTypeUpdate, ContentTypeInDB,
    ContentCreate, ContentUpdate, ContentInDB, ContentListResponse
)

router = APIRouter(prefix="/categories", tags=["categories"])

SYSTEM_CATEGORIES = [
    {"name": "个人", "icon": "👤", "color": "#00d4ff", "sort_order": 0},
    {"name": "工作", "icon": "💼", "color": "#7b2cbf", "sort_order": 1},
    {"name": "素材", "icon": "📦", "color": "#10b981", "sort_order": 2},
]

SYSTEM_CONTENT_TYPES = [
    {"category_name": "个人", "types": [
        {"name": "笔记", "icon": "📝", "color": "#00d4ff"},
        {"name": "日记", "icon": "📔", "color": "#f59e0b"},
        {"name": "简历", "icon": "📄", "color": "#8b5cf6"},
    ]},
    {"category_name": "工作", "types": [
        {"name": "业务知识", "icon": "📊", "color": "#7b2cbf"},
        {"name": "管理知识", "icon": "📈", "color": "#06b6d4"},
    ]},
    {"category_name": "素材", "types": [
        {"name": "图片", "icon": "🖼️", "color": "#10b981"},
        {"name": "链接", "icon": "🔗", "color": "#3b82f6"},
        {"name": "视频", "icon": "🎬", "color": "#ef4444"},
    ]},
]

async def init_system_categories(db: Session):
    existing = db.query(Category).first()
    if existing:
        return
    
    for cat_data in SYSTEM_CATEGORIES:
        category = Category(
            name=cat_data["name"],
            icon=cat_data["icon"],
            color=cat_data["color"],
            sort_order=cat_data["sort_order"],
            is_system=True
        )
        db.add(category)
    
    db.commit()
    
    for cat_types in SYSTEM_CONTENT_TYPES:
        category = db.query(Category).filter(Category.name == cat_types["category_name"]).first()
        if category:
            for type_data in cat_types["types"]:
                content_type = ContentType(
                    category_id=category.id,
                    name=type_data["name"],
                    icon=type_data["icon"],
                    color=type_data["color"],
                    is_system=True
                )
                db.add(content_type)
    
    db.commit()

@router.get("", response_model=Response[List[CategoryInDB]])
async def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await init_system_categories(db)
    categories = db.query(Category).order_by(Category.sort_order).all()
    return Response(data=categories)

@router.post("", response_model=Response[CategoryInDB])
async def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return Response(data=category, message="分类创建成功")

@router.put("/{category_id}", response_model=Response[CategoryInDB])
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    if category.is_system:
        raise HTTPException(status_code=400, detail="系统分类不可修改")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    
    db.commit()
    db.refresh(category)
    return Response(data=category, message="分类更新成功")

@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    if category.is_system:
        raise HTTPException(status_code=400, detail="系统分类不可删除")
    
    db.delete(category)
    db.commit()
    return Response(message="分类已删除")

@router.get("/{category_id}/types", response_model=Response[List[ContentTypeInDB]])
async def get_content_types(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    types = db.query(ContentType).filter(ContentType.category_id == category_id).all()
    return Response(data=types)

@router.post("/types", response_model=Response[ContentTypeInDB])
async def create_content_type(
    data: ContentTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = db.query(Category).filter(Category.id == data.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    content_type = ContentType(
        name=data.name,
        category_id=data.category_id,
        icon=data.icon,
        color=data.color,
        field_schema=json.dumps(data.field_schema) if data.field_schema else "{}"
    )
    db.add(content_type)
    db.commit()
    db.refresh(content_type)
    return Response(data=content_type, message="内容类型创建成功")

@router.put("/types/{type_id}", response_model=Response[ContentTypeInDB])
async def update_content_type(
    type_id: str,
    data: ContentTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content_type = db.query(ContentType).filter(ContentType.id == type_id).first()
    if not content_type:
        raise HTTPException(status_code=404, detail="内容类型不存在")
    
    if content_type.is_system:
        raise HTTPException(status_code=400, detail="系统内容类型不可修改")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "field_schema" and value is not None:
            value = json.dumps(value)
        setattr(content_type, key, value)
    
    db.commit()
    db.refresh(content_type)
    return Response(data=content_type, message="内容类型更新成功")

@router.delete("/types/{type_id}")
async def delete_content_type(
    type_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content_type = db.query(ContentType).filter(ContentType.id == type_id).first()
    if not content_type:
        raise HTTPException(status_code=404, detail="内容类型不存在")
    
    if content_type.is_system:
        raise HTTPException(status_code=400, detail="系统内容类型不可删除")
    
    db.delete(content_type)
    db.commit()
    return Response(message="内容类型已删除")
