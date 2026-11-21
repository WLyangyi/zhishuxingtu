# -*- coding: utf-8 -*-
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.agent_session import AgentSession, AgentTask, AgentToolCall
from app.models.user import User
from app.services.agent.graph import build_input, delete_thread, get_graph
from app.services.agent.config import CORE_INTENT_ENABLED
from app.services.agent.recovery import reconcile_recovery
from app.services.agent.nodes import (
    _apply_resume_merge,
    _extract_resume_changes,
    _now_iso,
    _sync_anchor_message,
)
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


class TaskCreateRequest(BaseModel):
    title: str = Field(default="新任务", max_length=500)
    goal: str = Field(default="")
    constraints: dict = Field(default_factory=dict)
    acceptance_criteria: List[str] = Field(default_factory=list)


class PreferenceUpdate(BaseModel):
    value: str = Field(..., min_length=1, max_length=2000)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------- Phase 4:每会话用量预算 ----------
def _turn_cost_cny(tokens: int) -> float:
    return round(tokens / 1000 * float(settings.AGENT_COST_PER_1K_TOKENS_CNY), 6)


def _session_budget_exhausted(session: AgentSession) -> Optional[str]:
    """返回超预算原因；未超出返回 None。"""
    tokens = int(session.total_tokens or 0)
    cost = float(session.total_cost_cny or 0.0)
    token_budget = int(settings.AGENT_SESSION_TOKEN_BUDGET)
    cost_budget = float(settings.AGENT_SESSION_COST_BUDGET_CNY)
    if token_budget > 0 and tokens >= token_budget:
        return f"累计 token {tokens} 已达会话上限 {token_budget}"
    if cost_budget > 0 and cost >= cost_budget:
        return f"累计花费 ¥{cost:.4f} 已达会话上限 ¥{cost_budget:.2f}"
    return None


def _budget_usage_payload(session: AgentSession, turn_tokens: int, turn_cost: float) -> dict:
    """用量字段(不含 type,由调用方决定是 usage 还是 budget_exceeded)。"""
    return {
        "turn_tokens": turn_tokens,
        "turn_cost_cny": round(turn_cost, 6),
        "session_tokens": int(session.total_tokens or 0),
        "session_cost_cny": round(float(session.total_cost_cny or 0.0), 6),
        "token_budget": int(settings.AGENT_SESSION_TOKEN_BUDGET),
        "cost_budget_cny": float(settings.AGENT_SESSION_COST_BUDGET_CNY),
    }


def _budget_exceeded_stream(session: AgentSession, reason: str) -> Iterator[str]:
    """预算耗尽时的硬停流:不调 LLM、不调工具,只回一条降级答复。"""
    usage = _budget_usage_payload(session, 0, 0.0)
    yield _sse({**usage, "type": "budget_exceeded", "message": f"会话预算已用尽:{reason}"})
    yield _sse(
        {
            "type": "final_answer",
            "answer": (
                f"本会话的用量预算已用尽（{reason}），已停止继续调用模型。\n\n"
                "你可以新建一个会话继续提问，或清空当前会话重新开始；"
                "如需长期使用请调高 AGENT_SESSION_TOKEN_BUDGET / AGENT_SESSION_COST_BUDGET_CNY。"
            ),
        }
    )
    yield "data: [DONE]\n\n"


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
    row.tool_call_id = tool_call_id
    row.tool_name = str(payload.get("tool_name") or "create_note")
    row.args_json = json.dumps(payload.get("args") or {}, ensure_ascii=False)
    row.result_json = json.dumps(
        {"title": payload.get("title"), "description": payload.get("description")},
        ensure_ascii=False,
    )
    row.latency_ms = 0
    # 三期3.1:execute_tool 已写 planned 行(operation_id 已设)时,不覆盖其生命周期状态,
    # 审批等待只是 planned 的子态,由 checkpoint interrupt 检测,不靠 status 字段。
    if not row.operation_id:
        row.status = "pending"
    db.commit()


def _persist_tool_logs(db: Session, session_id: str, logs: List[dict]) -> None:
    for log in logs:
        tool_call_id = str(log.get("tool_call_id") or uuid.uuid4())
        record_id = _record_id(session_id, tool_call_id)
        row = db.query(AgentToolCall).filter(AgentToolCall.id == record_id).first()
        # 三期3.1:execute_tool 已用 operation_id 管理生命周期(planned→succeeded/failed),
        # 路由层不再覆盖其状态/结果,只补无 operation_id 的 legacy 行。
        if row and row.operation_id:
            continue
        if not row:
            row = AgentToolCall(id=record_id, session_id=session_id)
            db.add(row)
        row.tool_call_id = tool_call_id
        row.tool_name = str(log.get("tool") or "")
        row.args_json = json.dumps(log.get("args") or {}, ensure_ascii=False)
        row.result_json = str(log.get("result") or "")[:2000]
        row.latency_ms = int(log.get("latency_ms") or 0)
        row.status = str(log.get("status") or "success")
    if logs:
        db.commit()


# 任务1.6/二期2.3:core_intent 终态回写(版本比较 + 历史去重,按 task 分区)
def _intent_history_entry(core_intent, intent_version, last_change):
    """历史快照条目(task/session 共用结构)。"""
    return {
        "version": intent_version,
        "goal": (core_intent or {}).get("goal", ""),
        "constraints": (core_intent or {}).get("constraints", {}) or {},
        "acceptance_criteria": (core_intent or {}).get("acceptance_criteria", []) or [],
        "change_type": last_change.get("change_type"),
        "source": last_change.get("source"),
        "confidence": last_change.get("confidence"),
        "unmapped_keys": last_change.get("unmapped_keys") or [],
        "ts": last_change.get("ts"),
    }


def _persist_core_intent(db: Session, session: AgentSession, values: Dict[str, Any]) -> None:
    """流正常完成时,把 checkpoint 里的 core_intent 回写。
    - 有 current_task_id → 写 task 表(二期2.3 按 task 分区);
    - 无 current_task_id → 写 session 镜像(一期 legacy 行为不变)。
    版本比较 + 历史去重,防旧值覆盖新值、防重复追加。checkpoint 是唯一真相源。"""
    core_intent = values.get("core_intent")
    intent_version = int(values.get("intent_version") or 0)
    last_change = values.get("last_intent_change")
    current_task_id = values.get("current_task_id")

    if current_task_id:
        task = db.query(AgentTask).filter_by(id=current_task_id).first()
        if task is None:
            return
        if intent_version < int(task.intent_version or 0):
            return  # task 镜像更新,不用旧 checkpoint 覆盖
        versions: List[dict] = []
        if task.intent_versions:
            try:
                versions = json.loads(task.intent_versions)
            except (TypeError, json.JSONDecodeError):
                versions = []
        if last_change and (not versions or versions[-1].get("version") != intent_version):
            versions.append(_intent_history_entry(core_intent, intent_version, last_change))
        task.goal = (core_intent or {}).get("goal", "") or ""
        task.constraints = json.dumps(
            (core_intent or {}).get("constraints", {}) or {}, ensure_ascii=False
        )
        task.acceptance_criteria = json.dumps(
            (core_intent or {}).get("acceptance_criteria", []) or [], ensure_ascii=False
        )
        task.intent_version = intent_version
        task.intent_versions = json.dumps(versions, ensure_ascii=False) if versions else None
        return

    # legacy:写 session 镜像(一期行为不变)
    session_version = int(session.intent_version or 0)
    if intent_version < session_version:
        return
    versions: List[dict] = []
    if session.intent_versions:
        try:
            versions = json.loads(session.intent_versions)
        except (TypeError, json.JSONDecodeError):
            versions = []
    if last_change and (not versions or versions[-1].get("version") != intent_version):
        versions.append(_intent_history_entry(core_intent, intent_version, last_change))
    session.core_intent = json.dumps(core_intent, ensure_ascii=False) if core_intent else None
    session.intent_version = intent_version
    session.intent_versions = json.dumps(versions, ensure_ascii=False) if versions else None


# 任务1.7/二期2.3:/sessions /messages 的 core_intent 返回(仅 on 模式,off/shadow 返回 null)
def _loads_json(raw, default):
    """安全解析 JSON 文本,失败/空返回 default。"""
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def _active_task_with_anchor(db: Session, session_id: str) -> Optional[AgentTask]:
    """会话当前有锚点的 active task(有 goal 或 constraints 才算有锚点)。"""
    task = db.query(AgentTask).filter_by(session_id=session_id, status="active").first()
    if task and (task.goal or task.constraints):
        return task
    return None


def _core_intent_summary(db: Session, session: AgentSession) -> Optional[dict]:
    """会话列表摘要:goal 前 80 字 + version(不取 intent_versions 整列)。
    有 active task 从 task 表读,无则从 session 镜像读(legacy)。"""
    task = _active_task_with_anchor(db, session.id)
    if task:
        return {"goal": (task.goal or "")[:80], "version": int(task.intent_version or 0)}
    if not session.core_intent:
        return None
    try:
        data = json.loads(session.core_intent)
    except (TypeError, json.JSONDecodeError):
        return None
    return {"goal": (data.get("goal") or "")[:80], "version": int(session.intent_version or 0)}


def _core_intent_full(db: Session, session: AgentSession) -> Optional[dict]:
    """会话详情完整 core_intent(锚点消息过滤后单独返回)。
    有 active task 从 task 表读,无则从 session 镜像读(legacy)。"""
    task = _active_task_with_anchor(db, session.id)
    if task:
        return {
            "goal": task.goal or "",
            "constraints": _loads_json(task.constraints, {}),
            "acceptance_criteria": _loads_json(task.acceptance_criteria, []),
        }
    if not session.core_intent:
        return None
    try:
        return json.loads(session.core_intent)
    except (TypeError, json.JSONDecodeError):
        return None


def _extract_interrupts(step: Dict[str, Any]) -> List[dict]:
    raw_interrupts = step.get("__interrupt__") or []
    payloads: List[dict] = []
    for item in raw_interrupts:
        value = getattr(item, "value", item)
        if isinstance(value, dict):
            payloads.append(value)
    return payloads


def _pending_approval_payload(snapshot: Any, session_id: str) -> Optional[dict]:
    """从 checkpoint 快照提取待审批 interrupt，用于前端刷新/切换后恢复审批卡。"""
    for task in getattr(snapshot, "tasks", None) or ():
        for interrupt_obj in getattr(task, "interrupts", None) or ():
            value = getattr(interrupt_obj, "value", interrupt_obj)
            if isinstance(value, dict) and value.get("type") == "approval_required":
                return {**value, "session_id": session_id}
    return None


# 任务0.3:并发 in-flight 标记(内存 dict,单进程假设,多 worker 留二期)
_IN_FLIGHT: dict[str, float] = {}
_IN_FLIGHT_TTL = 600  # 10 分钟兜底,防进程崩溃/客户端早断留下永久 409


def _acquire_in_flight(thread_id: str) -> bool:
    """尝试获取 in-flight 标记。已存在且未超时返回 False(应 409),成功获取返回 True。"""
    now = time.time()
    ts = _IN_FLIGHT.get(thread_id)
    if ts is not None and now - ts < _IN_FLIGHT_TTL:
        return False
    _IN_FLIGHT[thread_id] = now
    return True


def _release_in_flight(thread_id: str) -> None:
    _IN_FLIGHT.pop(thread_id, None)


def _is_in_flight(thread_id: str) -> bool:
    """只读检查 in-flight 标记(含 TTL),供恢复接口判断是否与运行中流冲突。"""
    now = time.time()
    ts = _IN_FLIGHT.get(thread_id)
    return ts is not None and now - ts < _IN_FLIGHT_TTL


def _resolve_stream_config(snapshot: Any, session_id: str) -> tuple[Optional[dict], str]:
    """根据 checkpoint 快照决定流式 config(任务0.2)。

    snapshot.next 是节点名元组,不是 interrupt;真实 interrupt 在 tasks[*].interrupts。
    - 有真实 interrupt → (None, "blocked"),路由层 409(待审批)
    - 无 interrupt 但有 pending next → 用 turn_start_checkpoint_id 重放,(config, "replay")
    - 无 pending → (默认 config, "normal")
    """
    if snapshot.next:
        has_interrupt = any(
            getattr(task, "interrupts", None)
            for task in (getattr(snapshot, "tasks", None) or ())
        )
        if has_interrupt:
            return None, "blocked"
        replay_id = (getattr(snapshot, "values", None) or {}).get("turn_start_checkpoint_id")
        if replay_id:
            return {
                "configurable": {"thread_id": session_id, "checkpoint_id": replay_id}
            }, "replay"
        return None, "blocked"
    return {"configurable": {"thread_id": session_id}}, "normal"


def _stream_graph(
    db: Session,
    graph_input: Any,
    session: AgentSession,
    user_id: str,
    fallback_question: str = "",
    emitted_offset: int = 0,
    config: Optional[dict] = None,
    in_flight_thread_id: Optional[str] = None,
    resume_merge: Optional[dict] = None,
) -> Iterator[str]:
    emitted = emitted_offset
    tool_logs: List[dict] = []
    final_answer = ""
    interrupted = False
    emitted_fallback = False
    turn_tokens = 0
    stream_ok = False

    stream_config = config if config is not None else build_stream_config(session.id, user_id=user_id)
    try:
        for step in get_graph().stream(graph_input, config=stream_config):
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
                # 任务1.6:pending_preference 流中写入——检测到立即 upsert_preference,
                # 不等终态。断流/中断也不丢全局偏好。失败不影响主流程。
                pending_pref = value.get("pending_preference")
                if pending_pref:
                    try:
                        upsert_preference(
                            db,
                            user_id,
                            str(pending_pref.get("key") or ""),
                            str(pending_pref.get("value") or ""),
                        )
                    except Exception:  # noqa: BLE001 偏好写入失败不阻断主流程
                        pass
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
                # token_used 是本轮累计值(每轮 build_input 清零),取 max 兼容中断恢复
                if isinstance(value.get("token_used"), int):
                    turn_tokens = max(turn_tokens, value["token_used"])
        stream_ok = True  # 流正常完成(未抛异常)
    except Exception as exc:  # noqa: BLE001
        yield _sse({"type": "error", "message": f"Agent 执行出错：{exc}"})
        if fallback_question:
            try:
                fallback = _fallback_answer(db, fallback_question)
            except Exception:
                fallback = "Agent 暂时不可用，请稍后重试。"
            yield _sse({"type": "final_answer", "answer": fallback})
            emitted_fallback = True
    finally:
        # 任务0.3:流结束释放 in-flight 标记,不残留永久 409(TTL 兜底客户端早断)
        if in_flight_thread_id:
            _release_in_flight(in_flight_thread_id)

    # 任务1.8:/resume 锚点合并——在 resume 流正常完成后 update_state(as_node) 合并锚点。
    # 必须在 resume 之后(update_state 会清空 pending interrupt,先做会破坏 resume 恢复)。
    # 图此时已在 END,update_state 不破坏任何东西;后续轮次从 checkpoint 读到合并后的锚点。
    if stream_ok and resume_merge:
        try:
            merge_values = {
                "core_intent": resume_merge["core_intent"],
                "intent_version": resume_merge["intent_version"],
                "last_intent_change": resume_merge["last_intent_change"],
            }
            if resume_merge.get("messages"):
                merge_values["messages"] = resume_merge["messages"]
            get_graph().update_state(
                build_stream_config(session.id, user_id=user_id), merge_values, as_node="intent_classify"
            )
        except Exception:  # noqa: BLE001 锚点合并失败不阻断主流程
            pass

    # M7.4:从图终态回写命中 agent 路由到会话(本地审计的 agent 维度,供路由准确率分析)
    # 重放场景 stream_config 带 checkpoint_id,回写须用默认 config 取 stream 后最新状态
    snapshot_values: Dict[str, Any] = {}
    try:
        _snapshot = get_graph().get_state(build_stream_config(session.id, user_id=user_id))
        snapshot_values = _snapshot.values or {}
        session.agent_route = (snapshot_values.get("current_agent") or "")[:32]
    except Exception:  # noqa: BLE001 审计回写失败不影响主流程
        session.agent_route = session.agent_route or ""

    _persist_tool_logs(db, session.id, tool_logs)
    # 任务1.6:core_intent 终态回写(仅流正常完成时)。pending_preference 已流中 upsert,不等终态。
    # resume 合并后的锚点已在 checkpoint,这里随终态一并回写 session 镜像。
    if stream_ok:
        try:
            _persist_core_intent(db, session, snapshot_values)
        except Exception:  # noqa: BLE001 锚点回写失败不影响主流程
            pass
    # Phase 4:跨轮累计用量,供每会话预算硬停与前端成本展示
    turn_cost = _turn_cost_cny(turn_tokens)
    session.total_tokens = int(session.total_tokens or 0) + turn_tokens
    session.total_cost_cny = round(float(session.total_cost_cny or 0.0) + turn_cost, 6)
    session.updated_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()

    if final_answer and not interrupted and not emitted_fallback:
        yield _sse({"type": "final_answer", "answer": final_answer})
    yield _sse({"type": "usage", **_budget_usage_payload(session, turn_tokens, turn_cost)})
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
    # Phase 4:会话预算已用尽则硬停,不调模型不调工具,直接回降级答复
    budget_reason = _session_budget_exhausted(session)
    if budget_reason:
        return StreamingResponse(
            _budget_exceeded_stream(session, budget_reason),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )
    # 任务0.3:in-flight 检查(最先),并发写直接 409
    if not _acquire_in_flight(session.id):
        raise HTTPException(status_code=409, detail="该会话正在处理中，请稍后重试")
    snapshot = get_graph().get_state(config)
    # 任务1.6:thread 无 checkpoint(messages 为空,如清空后重建)时,session 镜像视为过期,先重置
    if not snapshot.values.get("messages") and (
        session.core_intent or session.intent_versions
    ):
        session.core_intent = None
        session.intent_version = 0
        session.intent_versions = None
        db.add(session)
        db.commit()
    stream_config, mode = _resolve_stream_config(snapshot, session.id)
    if mode == "blocked":
        # 真实 interrupt(待审批)才拒绝新输入：langgraph 会静默丢弃挂起
        # 审批任务，并在历史中留下悬挂的 AIMessage(tool_calls)，导致后续轮次持续报错。
        _release_in_flight(session.id)
        raise HTTPException(status_code=409, detail="该会话有待审批操作，请先在审批卡中确认或拒绝")
    # Checkpoint 已有消息时不再接受客户端历史，避免每轮重复注入。
    effective_history = [] if snapshot.values.get("messages") else parsed_history
    graph_input = build_input(
        question,
        session_id=session.id,
        user_id=current_user.id,
        history=effective_history,
    )
    # 任务0.2:每轮写入当前 checkpoint_id,供断流后用它作 config 重放
    graph_input["turn_start_checkpoint_id"] = (snapshot.config or {}).get("configurable", {}).get("checkpoint_id", "") or ""
    # 三期3.4:断流重放(replay)前核对 planned 行副作用,SSE 推送恢复报告。
    # 核对确认的行补记 succeeded,后续 execute_tool 按 operation_id 幂等跳过重执行。
    recovery_report = None
    if mode == "replay":
        try:
            recovery_report = reconcile_recovery(session.id, current_user.id, db=db)
        except Exception:  # noqa: BLE001 恢复核对失败不阻断重放主流程
            recovery_report = None

    def _stream_with_recovery():
        if recovery_report is not None:
            yield _sse(
                {
                    "type": "recovery",
                    "session_id": session.id,
                    "report": recovery_report,
                }
            )
        yield from _stream_graph(
            db, graph_input, session, current_user.id,
            fallback_question=question, config=stream_config,
            in_flight_thread_id=session.id,
        )

    return StreamingResponse(
        _stream_with_recovery(),
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
    budget_reason = _session_budget_exhausted(session)
    if budget_reason:
        return StreamingResponse(
            _budget_exceeded_stream(session, budget_reason),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )
    # 任务0.3:resume 同样受 in-flight 约束
    if not _acquire_in_flight(session.id):
        raise HTTPException(status_code=409, detail="该会话正在处理中，请稍后重试")
    snapshot = get_graph().get_state(config)
    if not snapshot.next:
        _release_in_flight(session.id)
        raise HTTPException(status_code=409, detail="该会话没有待审批操作")
    question = str(snapshot.values.get("question") or "")
    emitted_offset = len(snapshot.values.get("thoughts") or [])
    # 任务1.8:/resume 合并——从审批理由抽取约束/偏好,计算合并锚点。
    # resume 当成一次 append:bump version、写 last_intent_change、source=resume、同 id 重建锚点消息。
    # 关键:update_state(as_node) 会清空 pending interrupt,不能在 resume 前做;
    # 合并锚点的 update_state 放到 _stream_graph 终态回写(resume 流完成之后)执行,避免破坏中断恢复。
    resume_merge = None
    if CORE_INTENT_ENABLED == "on":
        changes = _extract_resume_changes(request.reason)
        current_ci = snapshot.values.get("core_intent") or {}
        current_version = int(snapshot.values.get("intent_version") or 0)
        change = _apply_resume_merge(
            current_ci, current_version, changes["constraints"], changes["preference"]
        )
        # preference(scope=global) → 直接 upsert 长期偏好
        pref = changes["preference"]
        if pref and pref.get("scope") == "global":
            try:
                upsert_preference(db, current_user.id, pref["key"], pref["value"])
            except Exception:  # noqa: BLE001 偏好写入失败不阻断 resume
                pass
        if change:
            new_anchor, new_version, applied_ct, source = change
            pseudo_state = {
                "session_id": session.id,
                "messages": snapshot.values.get("messages") or [],
            }
            anchor_msgs = _sync_anchor_message(pseudo_state, new_anchor)
            resume_merge = {
                "core_intent": new_anchor,
                "intent_version": new_version,
                "last_intent_change": {"change_type": applied_ct, "source": source, "ts": _now_iso()},
                "messages": anchor_msgs,
            }
    command = Command(resume={"approved": request.approved, "reason": request.reason})
    return StreamingResponse(
        _stream_graph(
            db,
            command,
            session,
            current_user.id,
            fallback_question=question,
            emitted_offset=emitted_offset,
            in_flight_thread_id=session.id,
            resume_merge=resume_merge,
        ),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/sessions")
async def list_agent_sessions(
    q: Optional[str] = Query(None, description="按会话标题关键词过滤（大小写不敏感）"),
    limit: int = Query(50, ge=1, le=200, description="返回条数上限"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(AgentSession).filter(AgentSession.user_id == current_user.id)
    keyword = (q or "").strip()
    if keyword:
        # func.lower 兼容 SQLite 与 Postgres，避免大小写敏感导致漏匹配
        query = query.filter(func.lower(AgentSession.title).contains(keyword.lower()))
    sessions = query.order_by(AgentSession.updated_at.desc()).limit(limit).all()
    on_mode = CORE_INTENT_ENABLED == "on"
    return {
        "success": True,
        "code": 200,
        "data": [
            {
                "id": session.id,
                "title": session.title,
                "total_tokens": int(session.total_tokens or 0),
                "total_cost_cny": round(float(session.total_cost_cny or 0.0), 6),
                "core_intent": _core_intent_summary(db, session) if on_mode else None,
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


# ---------- 二期2.6:task 创建/切换/恢复接口 ----------
def _task_payload(task: AgentTask) -> dict:
    return {
        "id": task.id,
        "session_id": task.session_id,
        "title": task.title,
        "goal": task.goal,
        "constraints": _loads_json(task.constraints, {}),
        "acceptance_criteria": _loads_json(task.acceptance_criteria, []),
        "phase": task.phase,
        "status": task.status,
        "depends_on": task.depends_on,
        "intent_version": int(task.intent_version or 0),
        "is_current": task.status == "active",
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


def _complete_active_task(db: Session, session_id: str, exclude_id: Optional[str] = None) -> None:
    """完成会话当前 active 任务(部分唯一索引释放名额),排除指定任务。"""
    tasks = db.query(AgentTask).filter_by(session_id=session_id, status="active").all()
    for t in tasks:
        if exclude_id and t.id == exclude_id:
            continue
        t.status = "completed"


def _set_current_task_in_state(session_id: str, user_id: str, task_id: str) -> None:
    """把 current_task_id 写入图状态(checkpoint)。无 checkpoint 时 fail-silent。"""
    try:
        get_graph().update_state(
            build_stream_config(session_id, user_id=user_id),
            {"current_task_id": task_id},
            as_node="intent_classify",
        )
    except Exception:  # noqa: BLE001 图状态写入失败不阻断接口
        pass


@router.post("/sessions/{session_id}/tasks")
async def create_agent_task(
    session_id: str,
    request: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_owned_session(db, current_user.id, session_id)
    _complete_active_task(db, session.id)
    task = AgentTask(
        session_id=session.id,
        user_id=current_user.id,
        title=(request.title or "新任务")[:500],
        goal=request.goal,
        constraints=json.dumps(request.constraints, ensure_ascii=False) if request.constraints else None,
        acceptance_criteria=json.dumps(request.acceptance_criteria, ensure_ascii=False) if request.acceptance_criteria else None,
        status="active",
        phase="clarify",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    _set_current_task_in_state(session.id, current_user.id, task.id)
    return {"success": True, "code": 200, "data": _task_payload(task)}


@router.get("/sessions/{session_id}/tasks")
async def list_agent_tasks(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_owned_session(db, current_user.id, session_id)
    tasks = (
        db.query(AgentTask)
        .filter_by(session_id=session.id)
        .order_by(AgentTask.created_at.desc())
        .all()
    )
    return {"success": True, "code": 200, "data": [_task_payload(t) for t in tasks]}


@router.post("/sessions/{session_id}/tasks/{task_id}/switch")
async def switch_agent_task(
    session_id: str,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_owned_session(db, current_user.id, session_id)
    task = db.query(AgentTask).filter_by(id=task_id, session_id=session.id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    _complete_active_task(db, session.id, exclude_id=task.id)
    task.status = "active"
    db.commit()
    db.refresh(task)
    _set_current_task_in_state(session.id, current_user.id, task.id)
    return {"success": True, "code": 200, "data": _task_payload(task)}


@router.post("/sessions/{session_id}/tasks/{task_id}/restore")
async def restore_agent_task(
    session_id: str,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_owned_session(db, current_user.id, session_id)
    task = db.query(AgentTask).filter_by(id=task_id, session_id=session.id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status == "active":
        return {"success": True, "code": 200, "data": _task_payload(task)}
    _complete_active_task(db, session.id, exclude_id=task.id)
    task.status = "active"
    db.commit()
    db.refresh(task)
    _set_current_task_in_state(session.id, current_user.id, task.id)
    return {"success": True, "code": 200, "data": _task_payload(task)}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_owned_session(db, current_user.id, session_id)
    snapshot = get_graph().get_state({"configurable": {"thread_id": session_id}})
    messages = []
    for message in snapshot.values.get("messages") or []:
        content = message.content if isinstance(message.content, str) else str(message.content)
        if isinstance(message, HumanMessage) and content:
            messages.append({"role": "user", "content": content})
        elif isinstance(message, AIMessage) and content:
            messages.append({"role": "assistant", "content": content})
    pending_approval = _pending_approval_payload(snapshot, session_id)
    on_mode = CORE_INTENT_ENABLED == "on"
    return {
        "success": True,
        "code": 200,
        "data": {
            "messages": messages,
            "pending_approval": pending_approval,
            "core_intent": _core_intent_full(db, session) if on_mode else None,
        },
    }


@router.get("/sessions/{session_id}/recovery")
async def get_session_recovery(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """三期3.5:断流恢复核对接口。

    检查顺序与 chat_stream 一致:in-flight → 真实 interrupt → 恢复核对。
    - in_flight:会话正在处理中,不核对(避免与运行中流冲突)
    - blocked:有待审批 interrupt,优先提示审批
    - ready:核对 planned 行副作用,返回恢复报告(confirmed/unknown)
    """
    session = _get_owned_session(db, current_user.id, session_id)
    if _is_in_flight(session.id):
        return {
            "success": True,
            "code": 200,
            "data": {"status": "in_flight", "recovery": None},
        }
    snapshot = get_graph().get_state({"configurable": {"thread_id": session.id}})
    pending_approval = _pending_approval_payload(snapshot, session.id)
    if pending_approval:
        return {
            "success": True,
            "code": 200,
            "data": {"status": "blocked", "pending_approval": pending_approval, "recovery": None},
        }
    try:
        report = reconcile_recovery(session.id, current_user.id, db=db)
    except Exception:  # noqa: BLE001 核对失败返回空报告,不阻断接口
        report = None
    return {
        "success": True,
        "code": 200,
        "data": {"status": "ready", "recovery": report},
    }


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
