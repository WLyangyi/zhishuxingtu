"""M5 trace 查询：Langfuse 优先，本地 agent_tool_calls 自动降级。"""
import json
from collections import Counter
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agent_session import AgentSession, AgentToolCall, UserPreference


def langfuse_configured() -> bool:
    return bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY)


def _safe_json(value: Optional[str]) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def list_local_traces(
    db: Session,
    user_id: str,
    page: int = 1,
    limit: int = 20,
) -> Dict[str, Any]:
    query = db.query(AgentSession).filter(AgentSession.user_id == user_id)
    total = query.count()
    sessions = (
        query.order_by(AgentSession.updated_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    data: List[dict] = []
    for session in sessions:
        calls = (
            db.query(AgentToolCall)
            .filter(AgentToolCall.session_id == session.id)
            .order_by(AgentToolCall.created_at.asc())
            .all()
        )
        statuses = [call.status or "success" for call in calls]
        if "pending" in statuses:
            status = "pending"
        elif "error" in statuses:
            status = "error"
        elif "rejected" in statuses:
            status = "rejected"
        else:
            status = "success"
        data.append(
            {
                "id": session.id,
                "session_id": session.id,
                "name": session.title or "Agent 会话",
                "timestamp": session.updated_at.isoformat() if session.updated_at else None,
                "latency_ms": sum(call.latency_ms or 0 for call in calls),
                "total_cost": None,
                "total_tokens": None,
                "tool_calls": len(calls),
                "status": status,
                "source": "local",
                "url": None,
            }
        )
    return {
        "source": "local",
        "data": data,
        "meta": {
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
        },
    }


def list_langfuse_traces(
    user_id: str,
    page: int = 1,
    limit: int = 20,
) -> Dict[str, Any]:
    if not langfuse_configured():
        raise RuntimeError("Langfuse 未配置")

    from langfuse import Langfuse

    client = Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        base_url=settings.LANGFUSE_BASE_URL,
        timeout=settings.LANGFUSE_TIMEOUT,
        tracing_enabled=False,
    )
    response = client.api.trace.list(
        page=page,
        limit=limit,
        user_id=user_id,
        order_by="timestamp.desc",
        fields="core,io,metrics",
    )
    data: List[dict] = []
    for trace in response.data:
        raw = trace.model_dump(mode="json", by_alias=True)
        error_count = int(raw.get("errorCount") or 0)
        total_tokens = raw.get("totalTokens") or raw.get("tokens")
        data.append(
            {
                "id": trace.id,
                "session_id": trace.session_id,
                "name": trace.name or "Agent trace",
                "timestamp": trace.timestamp.isoformat(),
                "latency_ms": round((trace.latency or 0) * 1000),
                "total_cost": trace.total_cost,
                "total_tokens": total_tokens,
                "tool_calls": len(trace.observations or []),
                "status": "error" if error_count else "success",
                "source": "langfuse",
                "url": urljoin(settings.LANGFUSE_BASE_URL.rstrip("/") + "/", trace.html_path.lstrip("/")),
            }
        )
    return {
        "source": "langfuse",
        "data": data,
        "meta": {
            "page": response.meta.page,
            "limit": response.meta.limit,
            "total_items": response.meta.total_items,
            "total_pages": response.meta.total_pages,
        },
    }


def list_traces(
    db: Session,
    user_id: str,
    source: str = "auto",
    page: int = 1,
    limit: int = 20,
) -> Dict[str, Any]:
    if source in {"auto", "langfuse"} and langfuse_configured():
        try:
            return list_langfuse_traces(user_id, page, limit)
        except Exception as exc:  # noqa: BLE001
            if source == "langfuse":
                raise
            result = list_local_traces(db, user_id, page, limit)
            result["fallback_reason"] = str(exc)
            return result
    return list_local_traces(db, user_id, page, limit)


def observability_summary(db: Session, user_id: str) -> Dict[str, Any]:
    session_rows = (
        db.query(AgentSession.id, AgentSession.agent_route)
        .filter(AgentSession.user_id == user_id)
        .all()
    )
    session_ids = [row[0] for row in session_rows]
    calls = (
        db.query(AgentToolCall)
        .filter(AgentToolCall.session_id.in_(session_ids))
        .all()
        if session_ids
        else []
    )
    statuses = Counter(call.status or "success" for call in calls)
    distribution = Counter(call.tool_name or "unknown" for call in calls)
    total_calls = len(calls)
    successful = statuses.get("success", 0)
    avg_latency = round(sum(call.latency_ms or 0 for call in calls) / total_calls) if total_calls else 0
    # M7.4:agent 路由分布(最近一轮命中的子 Agent;空串为 M7 前的旧会话)
    route_counter = Counter(row[1] or "" for row in session_rows)
    return {
        "sessions": len(session_ids),
        "tool_calls": total_calls,
        "avg_tool_latency_ms": avg_latency,
        "success_rate": round(successful / total_calls, 4) if total_calls else 1.0,
        "pending_approvals": statuses.get("pending", 0),
        "rejected_calls": statuses.get("rejected", 0),
        "preferences": db.query(func.count(UserPreference.id)).filter(UserPreference.user_id == user_id).scalar() or 0,
        "tool_distribution": [
            {"name": name, "count": count}
            for name, count in distribution.most_common()
        ],
        "agent_route_distribution": [
            {"name": name or "legacy", "count": count}
            for name, count in route_counter.most_common()
        ],
        "langfuse_configured": langfuse_configured(),
    }


def session_timeline(db: Session, session_id: str) -> List[dict]:
    calls = (
        db.query(AgentToolCall)
        .filter(AgentToolCall.session_id == session_id)
        .order_by(AgentToolCall.created_at.asc())
        .all()
    )
    return [
        {
            "id": call.id,
            "type": "tool",
            "tool_name": call.tool_name,
            "args": _safe_json(call.args_json),
            "result": _safe_json(call.result_json),
            "latency_ms": call.latency_ms or 0,
            "status": call.status or "success",
            "created_at": call.created_at.isoformat() if call.created_at else None,
        }
        for call in calls
    ]
