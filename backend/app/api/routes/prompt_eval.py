from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime
from app.api.deps import get_db, get_current_user
from app.models.few_shot import PromptEvaluation
from app.models.user import User
from app.schemas.prompt_eval import (
    PromptEvaluationCreate, PromptEvaluationInDB, 
    PromptEvaluationStats, PromptEvaluationWithAuto
)
from app.schemas.response import Response
from app.services.prompt_evaluator import get_prompt_evaluator

router = APIRouter()

@router.post("/", response_model=Response)
def create_evaluation(
    evaluation: PromptEvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_eval = PromptEvaluation(**evaluation.dict())
    db.add(db_eval)
    db.commit()
    db.refresh(db_eval)
    return Response(data=PromptEvaluationInDB.from_orm(db_eval).dict(), message="评估记录创建成功")

@router.post("/auto-evaluate", response_model=Response)
async def auto_evaluate_response(
    question: str,
    response: str,
    context: Optional[str] = None,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    evaluator = get_prompt_evaluator()
    scores = evaluator.evaluate_response(question, response, context)
    
    db_eval = PromptEvaluation(
        session_id=session_id,
        question=question,
        response=response,
        context=context,
        relevance_score=scores["relevance_score"],
        accuracy_score=scores["accuracy_score"],
        completeness_score=scores["completeness_score"],
        clarity_score=scores["clarity_score"],
        overall_score=scores["overall_score"]
    )
    db.add(db_eval)
    db.commit()
    db.refresh(db_eval)
    
    return Response(data={
        "evaluation_id": db_eval.id,
        "scores": scores
    }, message="自动评估完成")

@router.get("/", response_model=Response)
def list_evaluations(
    prompt_version_id: Optional[str] = None,
    min_score: Optional[float] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(PromptEvaluation)
    
    if prompt_version_id:
        query = query.filter(PromptEvaluation.prompt_version_id == prompt_version_id)
    if min_score:
        query = query.filter(PromptEvaluation.overall_score >= min_score)
    
    evaluations = query.order_by(PromptEvaluation.created_at.desc()).limit(limit).all()
    return Response(data=[PromptEvaluationInDB.from_orm(e).dict() for e in evaluations])

@router.get("/stats", response_model=Response)
def get_evaluation_stats(
    prompt_version_id: Optional[str] = None,
    days: int = 7,
    db: Session = Depends(get_db)
):
    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(PromptEvaluation).filter(PromptEvaluation.created_at >= start_date)
    if prompt_version_id:
        query = query.filter(PromptEvaluation.prompt_version_id == prompt_version_id)
    
    evaluations = query.all()
    
    if not evaluations:
        return Response(data={
            "total_evaluations": 0,
            "avg_overall_score": None,
            "avg_relevance_score": None,
            "avg_accuracy_score": None,
            "avg_completeness_score": None,
            "avg_clarity_score": None
        })
    
    def calc_avg(field):
        values = [getattr(e, field) for e in evaluations if getattr(e, field) is not None]
        return sum(values) / len(values) if values else None
    
    stats = {
        "total_evaluations": len(evaluations),
        "avg_overall_score": calc_avg("overall_score"),
        "avg_relevance_score": calc_avg("relevance_score"),
        "avg_accuracy_score": calc_avg("accuracy_score"),
        "avg_completeness_score": calc_avg("completeness_score"),
        "avg_clarity_score": calc_avg("clarity_score"),
        "score_distribution": {
            "excellent": len([e for e in evaluations if e.overall_score and e.overall_score >= 8]),
            "good": len([e for e in evaluations if e.overall_score and 6 <= e.overall_score < 8]),
            "average": len([e for e in evaluations if e.overall_score and 4 <= e.overall_score < 6]),
            "poor": len([e for e in evaluations if e.overall_score and e.overall_score < 4])
        }
    }
    
    return Response(data=stats)

@router.post("/{evaluation_id}/feedback", response_model=Response)
def submit_user_feedback(
    evaluation_id: str,
    user_rating: int,
    user_feedback: Optional[str] = None,
    db: Session = Depends(get_db)
):
    evaluation = db.query(PromptEvaluation).filter(PromptEvaluation.id == evaluation_id).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="评估记录不存在")
    
    evaluation.user_rating = str(user_rating)
    if user_feedback:
        evaluation.user_feedback = user_feedback
    
    db.commit()
    return Response(message="用户反馈提交成功")
