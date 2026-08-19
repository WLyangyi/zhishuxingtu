# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.agent_session import AgentSession, AgentToolCall
from app.models.user import User
from app.services.agent.graph import build_input, delete_thread, get_graph
from app.services.agent.memory import (
    delete_preference,
    get_memory_store,
    list_preferences,
    upsert_preference,
)
from app.services.observability.langfuse_trace import build_stream_config
from app.services.observability.trace_service import (
    list_traces,
    observability_summary,
    session_timeline,
)

router = APIRouter(prefix="/agent", tags=["Agent"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class ResumeRequest(BaseModel):
    session_id: str
    approved: bool
    reason: str = ""


class PreferenceUpdate(BaseModel):
    value: str = Field(..., min_length=1, max_length=2000)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _fallback_answer(db: Session, question: str) -> str:
    """Agent 异常降级：复用旧混合检索 + 旧 LLM。"""
    from app.api.routes.search import hybrid_search_notes, keyword_search_notes
    from app.services.llm_service import get_llm_service
    from langchain_core.messages import HumanMessage as LCHumanMessage
    from langchain_core.messages import SystemMessage

    notes = hybrid_search_notes(question, db, k=5, use_reranker=True)
    if not notes:
        notes = keyword_search_notes(question, db, max_results=5)
    if not notes:
        return "抱歉，Agent 暂时不可用，且知识库中未检索到相关内容。"

    context = "\n\n".join(f"【笔记标题】{n.title}\n{(n.content or '')[:1500]}" for n, _ in notes)
    try:
        response = get_llm_service().invoke(
            [
                SystemMessage(content="你是知识库助手。仅根据给定笔记回答问题，不要编造。"),
                LCHumanMessage(content=f"笔记:\n{context}\n\n问题:{question}"),
            ]
        )
        return getattr(response, "content", "") or "Agent 暂时不可用，请稍后重试。"
    except Exception:
        return f"Agent 暂时不可用。已检索到相关笔记《{notes[0][0].title}》，请稍后重试。"


def _get_owned_session(db: Session, user_id: str, session_id: str) -> AgentSession:
    session = (
        db.query(AgentSession)
        .filter(AgentSession.id == session_id, AgentSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


def _get_or_create_session(
    db: Session,
    user_id: str,
    session_id: Optional[str],
    title: str,
) -> AgentSession:
    if session_id:
        existing = db.query(AgentSession).filter(AgentSession.id == session_id).first()
        if existing:
            if existing.user_id != user_id:
                raise HTTPException(status_code=404, detail="会话不存在")
            return existing
    session = AgentSession(id=session_id or str(uuid.uuid4()), user_id=user_id, title=title[:50])
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _record_id(session_id: str, tool_call_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"zhishuxingtu:{session_id}:{tool_call_id}"))


def _persist_pending_approval(db: Session, session_id: str, payload: Dict[str, Any]) -> None:
    tool_call_id = str(payload.get("tool_call_id") or "pending")
    record_id = _record_id(session_id, tool_call_id)
    row = db.query(AgentToolCall).filter(AgentToolCall.id == record_id).first()
    if not row:
        row = AgentToolCall(id=record_id, session_id=session_id)
        db.add(row)
    row.tool_name = str(payload.get("tool_name") or "create_note")
    row.args_json = json.dumps(payload.get("args") or {}, ensure_ascii=False)
    row.result_json = json.dumps(
        {"title": payload.get("title"), "description": payload.get("description")},
        ensure_ascii=False,
    )
    row.latency_ms = 0
    row.status = "pending"
    db.commit()


def _persist_tool_logs(db: Session, session_id: str, logs: List[dict]) -> None:
    for log in logs:
        tool_call_id = str(log.get("tool_call_id") or uuid.uuid4())
        record_id = _record_id(session_id, tool_call_id)
        row = db.query(AgentToolCall).filter(AgentToolCall.id == record_id).first()
        if not row:
            row = AgentToolCall(id=record_id, session_id=session_id)
            db.add(row)
        row.tool_name = str(log.get("tool") or "")
        row.args_json = json.dumps(log.get("args") or {}, ensure_ascii=False)
        row.result_json = str(log.get("result") or "")[:2000]
        row.latency_ms = int(log.get("latency_ms") or 0)
        row.status = str(log.get("status") or "success")
    if logs:
        db.commit()


def _extract_interrupts(step: Dict[str, Any]) -> List[dict]:
    raw_interrupts = step.get("__interrupt__") or []
    payloads: List[dict] = []
    for item in raw_interrupts:
        value = getattr(item, "value", item)
        if isinstance(value, dict):
            payloads.append(value)
    return payloads


def _stream_graph(
    db: Session,
    graph_input: Any,
    session: AgentSession,
    user_id: str,
    fallback_question: str = "",
    emitted_offset: int = 0,
) -> Iterator[str]:
    emitted = emitted_offset
    tool_logs: List[dict] = []
    final_answer = ""
    interrupted = False
    emitted_fallback = False

    try:
        config = build_stream_config(session.id, user_id=user_id)
        for step in get_graph().stream(graph_input, config=config):
            interrupt_payloads = _extract_interrupts(step)
            if interrupt_payloads:
                interrupted = True
                for payload in interrupt_payloads:
                    _persist_pending_approval(db, session.id, payload)
                    yield _sse({**payload, "type": "approval_required", "session_id": session.id})
                continue

            for node_name, value in step.items():
                if not isinstance(value, dict):
                    continue
                thoughts = value.get("thoughts") or []
                for thought in thoughts[emitted:]:
                    emitted += 1
                    yield _sse(
                        {
                            "type": thought.get("type", "event"),
                            "content": thought.get("content", ""),
                            "node": node_name,
                        }
                    )
                if value.get("answer"):
                    final_answer = value["answer"]
                if value.get("tool_calls_log"):
                    tool_logs = value["tool_calls_log"]
    except Exception as exc:  # noqa: BLE001
        yield _sse({"type": "error", "message": f"Agent 执行出错：{exc}"})
        if fallback_question:
            try:
                fallback = _fallback_answer(db, fallback_question)
            except Exception:
                fallback = "Agent 暂时不可用，请稍后重试。"
            yield _sse({"type": "final_answer", "answer": fallback})
            emitted_fallback = True

    _persist_tool_logs(db, session.id, tool_logs)
    session.updated_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()

    if final_answer and not interrupted and not emitted_fallback:
        yield _sse({"type": "final_answer", "answer": final_answer})
    yield "data: [DONE]\n\n"


@router.post("/chat/stream")
async def agent_chat_stream(
    question: str = Query(..., min_length=1),
    session_id: Optional[str] = Query(None),
    history: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    parsed_history: List[dict] = []
    if history:
        try:
            parsed_history = json.loads(history)
        except (TypeError, json.JSONDecodeError):
            parsed_history = []

    session = _get_or_create_session(db, current_user.id, session_id, question)
    if session.title == "新会话":
        session.title = question[:50]
        db.add(session)
        db.commit()
    config = {"configurable": {"thread_id": session.id}}
    snapshot = get_graph().get_state(config)
    # Checkpoint 已有消息时不再接受客户端历史，避免每轮重复注入。
    effective_history = [] if snapshot.values.get("messages") else parsed_history
    graph_input = build_input(
        question,
        session_id=session.id,
        user_id=current_user.id,
        history=effective_history,
    )
    return StreamingResponse(
        _stream_graph(db, graph_input, session, current_user.id, fallback_question=question),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/resume")
async def resume_agent(
    request: ResumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_owned_session(db, current_user.id, request.session_id)
    config = {"configurable": {"thread_id": session.id}}
    snapshot = get_graph().get_state(config)
    if not snapshot.next:
        raise HTTPException(status_code=409, detail="该会话没有待审批操作")
    question = str(snapshot.values.get("question") or "")
    emitted_offset = len(snapshot.values.get("thoughts") or [])
    command = Command(resume={"approved": request.approved, "reason": request.reason})
    return StreamingResponse(
        _stream_graph(
            db,
            command,
            session,
            current_user.id,
            fallback_question=question,
            emitted_offset=emitted_offset,
        ),
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
                "id": session.id,
                "title": session.title,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            }
            for session in sessions
        ],
    }


@router.post("/sessions")
async def create_agent_session(
    title: Optional[str] = Query("新会话"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = AgentSession(user_id=current_user.id, title=(title or "新会话")[:50])
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"success": True, "code": 200, "data": {"id": session.id, "title": session.title}}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_session(db, current_user.id, session_id)
    snapshot = get_graph().get_state({"configurable": {"thread_id": session_id}})
    messages = []
    for message in snapshot.values.get("messages") or []:
        content = message.content if isinstance(message.content, str) else str(message.content)
        if isinstance(message, HumanMessage) and content:
            messages.append({"role": "user", "content": content})
        elif isinstance(message, AIMessage) and content:
            messages.append({"role": "assistant", "content": content})
    return {"success": True, "code": 200, "data": messages}


@router.delete("/sessions/{session_id}")
async def delete_agent_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_owned_session(db, current_user.id, session_id)
    db.query(AgentToolCall).filter(AgentToolCall.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    delete_thread(session_id)
    return {"success": True, "code": 200, "data": {"id": session_id}}


@router.delete("/sessions/{session_id}/messages")
async def clear_agent_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_session(db, current_user.id, session_id)
    delete_thread(session_id)
    db.query(AgentToolCall).filter(AgentToolCall.session_id == session_id).delete()
    db.commit()
    return {"success": True, "code": 200, "data": {"id": session_id}}


@router.get("/sessions/{session_id}/timeline")
async def get_session_timeline(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_session(db, current_user.id, session_id)
    return {"success": True, "code": 200, "data": session_timeline(db, session_id)}


@router.get("/preferences")
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"success": True, "code": 200, "data": list_preferences(db, current_user.id)}


@router.put("/preferences/{key}")
async def put_preference(
    key: str,
    request: PreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not key.strip() or len(key) > 100:
        raise HTTPException(status_code=422, detail="偏好键长度必须为 1-100")
    row = upsert_preference(db, current_user.id, key, request.value, get_memory_store())
    return {
        "success": True,
        "code": 200,
        "data": {"key": row.preference_key, "value": row.preference_value},
    }


@router.delete("/preferences/{key}")
async def remove_preference(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = delete_preference(db, current_user.id, key, get_memory_store())
    if not deleted:
        raise HTTPException(status_code=404, detail="偏好不存在")
    return {"success": True, "code": 200, "data": {"key": key}}


@router.get("/traces")
async def get_agent_traces(
    source: str = Query("auto", pattern="^(auto|local|langfuse)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = list_traces(db, current_user.id, source=source, page=page, limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Langfuse 查询失败：{exc}") from exc
    return {"success": True, "code": 200, "data": result}


@router.get("/observability/summary")
async def get_observability_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"success": True, "code": 200, "data": observability_summary(db, current_user.id)}
