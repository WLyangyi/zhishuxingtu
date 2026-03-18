from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.models.folder import Folder
from app.models.note import Note
from app.models.user import User
from app.models.category import Category
from app.schemas import Response, FolderCreate, FolderUpdate, FolderResponse, FolderTreeResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/folders", tags=["文件夹"])

def build_folder_tree(folders: List[Folder], db: Session, parent_id: str = None, category_id: str = None) -> List[dict]:
    result = []
    for folder in folders:
        if folder.parent_id == parent_id and (category_id is None or folder.category_id == category_id):
            direct_count = db.query(Note).filter(Note.folder_id == folder.id).count()
            children_count = sum_count_notes(folders, db, folder.id)
            total_count = direct_count + children_count

            folder_dict = FolderTreeResponse(
                id=folder.id,
                name=folder.name,
                parent_id=folder.parent_id,
                level=folder.level,
                category_id=folder.category_id,
                note_count=total_count,
                created_at=folder.created_at,
                children=build_folder_tree(folders, db, folder.id, category_id)
            ).model_dump()
            result.append(folder_dict)
    return result

def sum_count_notes(folders: List[Folder], db: Session, parent_id: str) -> int:
    total = 0
    for folder in folders:
        if folder.parent_id == parent_id:
            direct_count = db.query(Note).filter(Note.folder_id == folder.id).count()
            total += direct_count
            total += sum_count_notes(folders, db, folder.id)
    return total

@router.get("", response_model=Response[List[FolderTreeResponse]])
async def get_folders(
    category_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    folders = db.query(Folder).all()
    tree = build_folder_tree(folders, db, category_id=category_id)
    return Response(data=tree)

@router.post("", response_model=Response[FolderResponse])
async def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    level = 0
    if folder_data.parent_id:
        parent = db.query(Folder).filter(Folder.id == folder_data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="父文件夹不存在")
        if parent.level >= 3:
            raise HTTPException(status_code=400, detail="最多支持4层文件夹")
        level = parent.level + 1

    if folder_data.category_id:
        category = db.query(Category).filter(Category.id == folder_data.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")

    folder = Folder(
        name=folder_data.name,
        parent_id=folder_data.parent_id,
        level=level,
        category_id=folder_data.category_id
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)

    return Response(data=FolderResponse(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        level=folder.level,
        category_id=folder.category_id,
        note_count=0,
        created_at=folder.created_at
    ), message="文件夹创建成功")

@router.put("/{folder_id}", response_model=Response[FolderResponse])
async def update_folder(
    folder_id: str,
    folder_data: FolderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")

    if folder_data.name is not None:
        folder.name = folder_data.name

    if folder_data.category_id is not None:
        category = db.query(Category).filter(Category.id == folder_data.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")
        folder.category_id = folder_data.category_id

    db.commit()
    db.refresh(folder)

    note_count = db.query(Note).filter(Note.folder_id == folder_id).count()

    return Response(data=FolderResponse(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        level=folder.level,
        category_id=folder.category_id,
        note_count=note_count,
        created_at=folder.created_at
    ), message="文件夹更新成功")

@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")

    note_count = db.query(Note).filter(Note.folder_id == folder_id).count()
    if note_count > 0:
        raise HTTPException(status_code=400, detail="文件夹不为空，请先移动或删除笔记")

    children = db.query(Folder).filter(Folder.parent_id == folder_id).count()
    if children > 0:
        raise HTTPException(status_code=400, detail="文件夹包含子文件夹，请先删除子文件夹")

    db.delete(folder)
    db.commit()
    return Response(message="文件夹删除成功")
