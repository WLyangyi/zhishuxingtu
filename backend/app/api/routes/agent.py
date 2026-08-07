# -*- coding: utf-8 -*-
import json
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.agent_session import AgentSession, AgentToolCall
from app.models.user import User
from app.services.agent.graph import build_input, get_graph
from app.services.tools.context import ToolContext, reset_tool_context, set_tool_context

router = APIRouter(prefix="/agent", tags=["Agent"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _fallback_answer(db: Session, question: str) -> str:
    """Agent 异常降级:复用旧混合检索 + 旧 LLM(即旧 /api/search/ai 链路),给出兜底答案。"""
    from app.api.routes.search import hybrid_search_notes, keyword_search_notes
    from app.services.llm_service import get_llm_service
    from langchain_core.messages import HumanMessage, SystemMessage

    notes = hybrid_search_notes(question, db, k=5, use_reranker=True)
    if not notes:
        notes = keyword_search_notes(question, db, max_results=5)
    if not notes:
        return "抱歉,Agent 暂时不可用,且知识库中未检索到相关内容。"

    context = "\n\n".join(f"【笔记标题】{n.title}\n{(n.content or '')[:1500]}" for n, _ in notes)
    try:
        resp = get_llm_service().invoke([
            SystemMessage(content="你是知识库助手。仅根据给定笔记回答问题,不要编造。"),
            HumanMessage(content=f"笔记:\n{context}\n\n问题:{question}"),
        ])
        return getattr(resp, "content", "") or "Agent 暂时不可用,请稍后重试。"
    except Exception:
        return f"Agent 暂时不可用。已检索到相关笔记:《{notes[0][0].title}》,请稍后重试。"


def _get_or_create_session(db: Session, user_id: str, session_id: Optional[str], title: str) -> AgentSession:
    if session_id:
        s = db.query(AgentSession).filter(
            AgentSession.id == session_id, AgentSession.user_id == user_id
        ).first()
        if s:
            return s
    s = AgentSession(id=session_id or str(uuid.uuid4()), user_id=user_id, title=title[:50])
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _stream_agent(db: Session, question: str, session: AgentSession, user_id: str, history: List[dict]):
    token = set_tool_context(ToolContext(user_id=user_id, session_id=session.id))
    try:
        input_data = build_input(question, session_id=session.id, user_id=user_id, history=history)
        emitted = 0
        tool_log: List[dict] = []
        final_answer = ""

        try:
            for step in get_graph().stream(
                input_data, config={"configurable": {"thread_id": session.id}}
            ):
                for _node, v in step.items():
                    thoughts = v.get("thoughts") or []
                    for th in thoughts[emitted:]:
                        emitted += 1
                        yield _sse({
                            "type": th.get("type", "event"),
                            "content": th.get("content", ""),
                            "node": _node,
                        })
                    if v.get("answer"):
                        final_answer = v["answer"]
                    if v.get("tool_calls_log"):
                        tool_log = v["tool_calls_log"]
        except Exception as e:
            yield _sse({"type": "error", "message": f"Agent 执行出错,已降级到旧检索:{e}"})
            try:
                fb = _fallback_answer(db, question)
            except Exception:
                fb = "Agent 暂时不可用,请稍后重试。"
            yield _sse({"type": "final_answer", "answer": fb})

        if tool_log:
            for tc in tool_log:
                db.add(AgentToolCall(
                    session_id=session.id,
                    tool_name=tc.get("tool", ""),
                    args_json=json.dumps(tc.get("args", {}), ensure_ascii=False),
                    result_json=str(tc.get("result", ""))[:1000],
                    latency_ms=0,
                    status="success",
                ))
            db.commit()

        if final_answer:
            yield _sse({"type": "final_answer", "answer": final_answer})
        yield "data: [DONE]\n\n"
    finally:
        reset_tool_context(token)


@router.post("/chat/stream")
async def agent_chat_stream(
    question: str = Query(...),
    session_id: Optional[str] = Query(None),
    history: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    parsed_history: List[dict] = []
    if history:
        try:
            parsed_history = json.loads(history)
        except Exception:
            parsed_history = []

    session = _get_or_create_session(db, current_user.id, session_id, question)
    return StreamingResponse(
        _stream_agent(db, question, session, current_user.id, parsed_history),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/sessions")
async def list_agent_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(AgentSession)
        .filter(AgentSession.user_id == current_user.id)
        .order_by(AgentSession.updated_at.desc())
        .limit(50)
        .all()
    )
    return {
        "success": True,
        "code": 200,
        "data": [
            {
                "id": s.id,
                "title": s.title,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ],
    }


@router.post("/sessions")
async def create_agent_session(
    title: Optional[str] = Query("新会话"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = AgentSession(user_id=current_user.id, title=(title or "新会话")[:50])
    db.add(s)
    db.commit()
    db.refresh(s)
    return {
        "success": True,
        "code": 200,
        "data": {"id": s.id, "title": s.title},
    }
