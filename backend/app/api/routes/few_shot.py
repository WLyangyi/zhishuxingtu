from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.api.deps import get_db, get_current_user
from app.models.few_shot import FewShotExample
from app.models.user import User
from app.schemas.few_shot import (
    FewShotExampleCreate, FewShotExampleUpdate, FewShotExampleInDB
)
from app.schemas.response import Response

router = APIRouter()

@router.post("/", response_model=Response)
def create_few_shot_example(
    example: FewShotExampleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_example = FewShotExample(**example.dict())
    db.add(db_example)
    db.commit()
    db.refresh(db_example)
    return Response(data=FewShotExampleInDB.from_orm(db_example).dict(), message="Few-Shot示例创建成功")

@router.get("/", response_model=Response)
def list_few_shot_examples(
    scenario: Optional[str] = None,
    prompt_id: Optional[str] = None,
    min_quality: Optional[float] = None,
    db: Session = Depends(get_db)
):
    query = db.query(FewShotExample).filter(FewShotExample.is_active == True)
    
    if scenario:
        query = query.filter(FewShotExample.scenario == scenario)
    if prompt_id:
        query = query.filter(FewShotExample.prompt_id == prompt_id)
    if min_quality:
        query = query.filter(FewShotExample.quality_score >= min_quality)
    
    examples = query.order_by(FewShotExample.quality_score.desc()).all()
    return Response(data=[FewShotExampleInDB.from_orm(e).dict() for e in examples])

@router.get("/{example_id}", response_model=Response)
def get_few_shot_example(
    example_id: str,
    db: Session = Depends(get_db)
):
    example = db.query(FewShotExample).filter(FewShotExample.id == example_id).first()
    if not example:
        raise HTTPException(status_code=404, detail="Few-Shot示例不存在")
    return Response(data=FewShotExampleInDB.from_orm(example).dict())

@router.put("/{example_id}", response_model=Response)
def update_few_shot_example(
    example_id: str,
    example_update: FewShotExampleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_example = db.query(FewShotExample).filter(FewShotExample.id == example_id).first()
    if not db_example:
        raise HTTPException(status_code=404, detail="Few-Shot示例不存在")
    
    update_data = example_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_example, field, value)
    
    db.commit()
    db.refresh(db_example)
    return Response(data=FewShotExampleInDB.from_orm(db_example).dict(), message="Few-Shot示例更新成功")

@router.delete("/{example_id}", response_model=Response)
def delete_few_shot_example(
    example_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_example = db.query(FewShotExample).filter(FewShotExample.id == example_id).first()
    if not db_example:
        raise HTTPException(status_code=404, detail="Few-Shot示例不存在")
    
    db_example.is_active = False
    db.commit()
    return Response(message="Few-Shot示例删除成功")

@router.get("/scenarios/list", response_model=Response)
def list_scenarios(db: Session = Depends(get_db)):
    scenarios = db.query(FewShotExample.scenario).distinct().all()
    return Response(data=[s[0] for s in scenarios if s[0]])
