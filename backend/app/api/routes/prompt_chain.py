from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import json
from app.api.deps import get_db, get_current_user
from app.models.few_shot import PromptChain, ChainStep, ChainExecution
from app.models.user import User
from app.schemas.few_shot import (
    PromptChainCreate, PromptChainUpdate, PromptChainInDB,
    ChainStepCreate, ChainStepInDB,
    ChainExecutionCreate, ChainExecutionInDB
)
from app.schemas.response import Response
from app.services.prompt_chain_engine import get_chain_engine, PRESET_CHAINS

router = APIRouter()

@router.post("/", response_model=Response)
def create_chain(
    chain: PromptChainCreate,
    db: Session = Depends(get_db)
):
    db_chain = PromptChain(
        name=chain.name,
        description=chain.description
    )
    db.add(db_chain)
    db.flush()
    
    if chain.steps:
        for step in chain.steps:
            db_step = ChainStep(
                chain_id=db_chain.id,
                **step.model_dump()
            )
            db.add(db_step)
    
    db.commit()
    db.refresh(db_chain)
    return Response(data=PromptChainInDB.model_validate(db_chain).model_dump(), message="提示词链创建成功")

@router.get("/", response_model=Response)
def list_chains(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(PromptChain)
    if is_active is not None:
        query = query.filter(PromptChain.is_active == is_active)
    chains = query.order_by(PromptChain.created_at.desc()).all()
    return Response(data=[PromptChainInDB.model_validate(c).model_dump() for c in chains])

@router.get("/presets", response_model=Response)
def list_preset_chains():
    return Response(data=[
        {"type": k, **v} for k, v in PRESET_CHAINS.items()
    ])

@router.post("/presets/{chain_type}", response_model=Response)
def create_from_preset(
    chain_type: str,
    db: Session = Depends(get_db)
):
    engine = get_chain_engine()
    chain = engine.create_preset_chain(chain_type, db)
    if not chain:
        raise HTTPException(status_code=400, detail="无效的预设链类型")
    return Response(data=PromptChainInDB.model_validate(chain).model_dump(), message="预设链创建成�?)

@router.get("/{chain_id}", response_model=Response)
def get_chain(
    chain_id: str,
    db: Session = Depends(get_db)
):
    chain = db.query(PromptChain).filter(PromptChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="提示词链不存�?)
    return Response(data=PromptChainInDB.model_validate(chain).model_dump())

@router.put("/{chain_id}", response_model=Response)
def update_chain(
    chain_id: str,
    chain_update: PromptChainUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chain = db.query(PromptChain).filter(PromptChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="提示词链不存�?)
    
    update_data = chain_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(chain, field, value)
    
    db.commit()
    db.refresh(chain)
    return Response(data=PromptChainInDB.model_validate(chain).model_dump(), message="提示词链更新成功")

@router.delete("/{chain_id}", response_model=Response)
def delete_chain(
    chain_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chain = db.query(PromptChain).filter(PromptChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="提示词链不存�?)
    
    chain.is_active = False
    db.commit()
    return Response(message="提示词链删除成功")

@router.post("/{chain_id}/steps", response_model=Response)
def add_step(
    chain_id: str,
    step: ChainStepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chain = db.query(PromptChain).filter(PromptChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="提示词链不存�?)
    
    db_step = ChainStep(
        chain_id=chain_id,
        **step.model_dump()
    )
    db.add(db_step)
    db.commit()
    db.refresh(db_step)
    return Response(data=ChainStepInDB.model_validate(db_step).model_dump(), message="步骤添加成功")

@router.delete("/{chain_id}/steps/{step_id}", response_model=Response)
def delete_step(
    chain_id: str,
    step_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    step = db.query(ChainStep).filter(
        ChainStep.id == step_id,
        ChainStep.chain_id == chain_id
    ).first()
    if not step:
        raise HTTPException(status_code=404, detail="步骤不存�?)
    
    db.delete(step)
    db.commit()
    return Response(message="步骤删除成功")

@router.post("/{chain_id}/execute", response_model=Response)
def execute_chain(
    chain_id: str,
    input_data: dict,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    chain = db.query(PromptChain).filter(PromptChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="提示词链不存�?)
    
    if not chain.is_active:
        raise HTTPException(status_code=400, detail="提示词链未激�?)
    
    engine = get_chain_engine()
    result = engine.execute_chain(chain, input_data, db, session_id)
    
    return Response(data=result, message="链执行完�? if result["success"] else "链执行失�?)

@router.get("/{chain_id}/executions", response_model=Response)
def list_executions(
    chain_id: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    executions = db.query(ChainExecution).filter(
        ChainExecution.chain_id == chain_id
    ).order_by(ChainExecution.started_at.desc()).limit(limit).all()
    
    return Response(data=[ChainExecutionInDB.model_validate(e).model_dump() for e in executions])

@router.get("/executions/{execution_id}", response_model=Response)
def get_execution(
    execution_id: str,
    db: Session = Depends(get_db)
):
    execution = db.query(ChainExecution).filter(ChainExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存�?)
    return Response(data=ChainExecutionInDB.model_validate(execution).model_dump())
