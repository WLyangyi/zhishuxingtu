from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime
import hashlib
from app.api.deps import get_db, get_current_user
from app.models.few_shot import PromptVersion, ABExperiment, ABTestResult
from app.models.user import User
from app.schemas.few_shot import (
    PromptVersionCreate, PromptVersionUpdate, PromptVersionInDB,
    ABExperimentCreate, ABExperimentUpdate, ABExperimentInDB,
    ABTestResultCreate, ABTestResultInDB, ABExperimentStats
)
from app.schemas.response import Response

router = APIRouter()

@router.post("/versions", response_model=Response)
def create_prompt_version(
    version: PromptVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_version = PromptVersion(**version.dict())
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    return Response(data=PromptVersionInDB.from_orm(db_version).dict(), message="提示词版本创建成功")

@router.get("/versions", response_model=Response)
def list_prompt_versions(
    prompt_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(PromptVersion).filter(PromptVersion.is_active == True)
    if prompt_id:
        query = query.filter(PromptVersion.prompt_id == prompt_id)
    versions = query.order_by(PromptVersion.created_at.desc()).all()
    return Response(data=[PromptVersionInDB.from_orm(v).dict() for v in versions])

@router.post("/experiments", response_model=Response)
def create_ab_experiment(
    experiment: ABExperimentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_experiment = ABExperiment(**experiment.dict(), start_time=datetime.utcnow())
    db.add(db_experiment)
    db.commit()
    db.refresh(db_experiment)
    return Response(data=ABExperimentInDB.from_orm(db_experiment).dict(), message="A/B实验创建成功")

@router.get("/experiments", response_model=Response)
def list_ab_experiments(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ABExperiment)
    if status:
        query = query.filter(ABExperiment.status == status)
    experiments = query.order_by(ABExperiment.created_at.desc()).all()
    return Response(data=[ABExperimentInDB.from_orm(e).dict() for e in experiments])

@router.post("/experiments/{experiment_id}/start", response_model=Response)
def start_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    experiment = db.query(ABExperiment).filter(ABExperiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="实验不存在")
    
    experiment.status = "running"
    experiment.start_time = datetime.utcnow()
    db.commit()
    return Response(message="实验已启动")

@router.post("/experiments/{experiment_id}/pause", response_model=Response)
def pause_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    experiment = db.query(ABExperiment).filter(ABExperiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="实验不存在")
    
    experiment.status = "paused"
    db.commit()
    return Response(message="实验已暂停")

@router.post("/experiments/{experiment_id}/assign", response_model=Response)
def assign_version(
    experiment_id: str,
    session_id: str,
    db: Session = Depends(get_db)
):
    experiment = db.query(ABExperiment).filter(ABExperiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="实验不存在")
    
    if experiment.status != "running":
        raise HTTPException(status_code=400, detail="实验未运行")
    
    hash_value = int(hashlib.md5(f"{experiment_id}{session_id}".encode()).hexdigest(), 16)
    assigned_version = "A" if (hash_value % 100) / 100 < experiment.traffic_split else "B"
    
    version_id = experiment.version_a_id if assigned_version == "A" else experiment.version_b_id
    
    return Response(data={
        "assigned_version": assigned_version,
        "version_id": version_id
    })

@router.post("/experiments/{experiment_id}/results", response_model=Response)
def submit_test_result(
    experiment_id: str,
    result: ABTestResultCreate,
    db: Session = Depends(get_db)
):
    experiment = db.query(ABExperiment).filter(ABExperiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="实验不存在")
    
    db_result = ABTestResult(**result.dict())
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return Response(data=ABTestResultInDB.from_orm(db_result).dict(), message="测试结果提交成功")

@router.get("/experiments/{experiment_id}/stats", response_model=Response)
def get_experiment_stats(
    experiment_id: str,
    db: Session = Depends(get_db)
):
    experiment = db.query(ABExperiment).filter(ABExperiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="实验不存在")
    
    results_a = db.query(ABTestResult).filter(
        ABTestResult.experiment_id == experiment_id,
        ABTestResult.version_id == experiment.version_a_id
    ).all()
    
    results_b = db.query(ABTestResult).filter(
        ABTestResult.experiment_id == experiment_id,
        ABTestResult.version_id == experiment.version_b_id
    ).all()
    
    def calc_avg_feedback(results):
        if not results:
            return None
        feedbacks = [r.user_feedback for r in results if r.user_feedback]
        return sum(feedbacks) / len(feedbacks) if feedbacks else None
    
    def calc_avg_response_time(results):
        if not results:
            return None
        times = [int(r.response_time_ms) for r in results if r.response_time_ms]
        return sum(times) / len(times) if times else None
    
    stats = ABExperimentStats(
        experiment_id=experiment_id,
        experiment_name=experiment.name,
        version_a_id=experiment.version_a_id,
        version_b_id=experiment.version_b_id,
        total_samples=len(results_a) + len(results_b),
        version_a_samples=len(results_a),
        version_b_samples=len(results_b),
        version_a_avg_feedback=calc_avg_feedback(results_a),
        version_b_avg_feedback=calc_avg_feedback(results_b),
        version_a_avg_response_time=calc_avg_response_time(results_a),
        version_b_avg_response_time=calc_avg_response_time(results_b)
    )
    
    return Response(data=stats.dict())
