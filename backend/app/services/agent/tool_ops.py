# -*- coding: utf-8 -*-
"""三期 3.1-3.2:工具调用操作级登记与状态映射。

operation_id 是业务级幂等键(session + tool_name + args 哈希),驱动 agent_tool_calls
行 planned → succeeded/failed 生命周期:
- execute_tool 在调用工具前先写 planned 行(operation_id + 参数摘要),执行后更新;
- 断流/重启后恢复时,按 operation_id 调 query_result 核对副作用是否已落地。

与现有写幂等键 agent:{session_id}:{tool_call_id}(Note.idempotency_key)衔接:
operation_id 是更高层业务键,同参数重放产出相同值,用于跳过已成功的重复执行;
note 级幂等键兜底实际落库,两者互补。
"""
import hashlib
import json
import uuid
from typing import Any, Optional

from app.db.session import SessionLocal
from app.models.agent_session import AgentToolCall

STATUS_PLANNED = "planned"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"


def compute_operation_id(session_id: str, tool_name: str, args: dict) -> str:
    """业务级幂等键:session + tool_name + 规范化 args 哈希。

    同一次业务操作(相同参数)重放/重试产出相同 operation_id,与模型侧 tool_call_id
    解耦——不同 tool_call_id 的同参数调用视为同一操作。
    """
    payload = json.dumps(
        {"tool": tool_name, "args": args or {}}, sort_keys=True, ensure_ascii=False
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:24]
    return f"op:{session_id}:{tool_name}:{digest}"


def _record_id(session_id: str, tool_call_id: str) -> str:
    """与路由层 _record_id 一致:uuid5(session_id, tool_call_id)。"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"zhishuxingtu:{session_id}:{tool_call_id}"))


def register_planned(
    session_id: str,
    tool_call_id: str,
    tool_name: str,
    args: dict,
    operation_id: str,
    db=None,
) -> AgentToolCall:
    """调用工具前写 planned 行(operation_id + 参数摘要 + status=planned)。

    幂等:同一 (session, tool_call_id) 已有行则更新为 planned,不产生新行。
    返回该行。db 为 None 时自开 SessionLocal(节点内调用),否则用传入的(测试注入)。
    """
    own = db is None
    db = db or SessionLocal()
    try:
        row = (
            db.query(AgentToolCall)
            .filter(AgentToolCall.id == _record_id(session_id, tool_call_id))
            .first()
        )
        if not row:
            row = AgentToolCall(id=_record_id(session_id, tool_call_id), session_id=session_id)
            db.add(row)
        row.tool_call_id = tool_call_id
        row.operation_id = operation_id
        row.tool_name = tool_name
        row.args_json = json.dumps(args or {}, ensure_ascii=False)[:2000]
        row.result_json = None
        row.latency_ms = 0
        row.status = STATUS_PLANNED
        db.commit()
        db.refresh(row)
        return row
    finally:
        if own:
            db.close()


def update_result(
    session_id: str,
    tool_call_id: str,
    status: str,
    result: str,
    latency_ms: int,
    db=None,
) -> None:
    """执行后更新行状态为 succeeded/failed,写结果与耗时。行不存在则跳过。"""
    own = db is None
    db = db or SessionLocal()
    try:
        row = (
            db.query(AgentToolCall)
            .filter(AgentToolCall.id == _record_id(session_id, tool_call_id))
            .first()
        )
        if not row:
            return
        row.status = status
        row.result_json = (result or "")[:2000]
        row.latency_ms = max(0, int(latency_ms))
        db.commit()
    finally:
        if own:
            db.close()


def query_result(session_id: str, operation_id: str, db=None) -> Optional[dict]:
    """按 operation_id 查结果,供恢复核对。返回 {status, result, tool_name} 或 None。"""
    own = db is None
    db = db or SessionLocal()
    try:
        row = (
            db.query(AgentToolCall)
            .filter(
                AgentToolCall.session_id == session_id,
                AgentToolCall.operation_id == operation_id,
            )
            .first()
        )
        if not row:
            return None
        return {
            "status": row.status,
            "result": row.result_json,
            "tool_name": row.tool_name,
            "tool_call_id": row.tool_call_id,
        }
    finally:
        if own:
            db.close()


def find_succeeded_by_operation(session_id: str, operation_id: str, db=None) -> Optional[dict]:
    """查已成功完成的操作(幂等命中),返回 {status, result}。未成功或不存在返回 None。"""
    res = query_result(session_id, operation_id, db=db)
    if res and res["status"] == STATUS_SUCCEEDED:
        return res
    return None


def verify_note_created(session_id: str, user_id: str, tool_call_id: str, db=None) -> bool:
    """核对 create_note 副作用是否真落地(Note 已按 idempotency_key 落库)。

    幂等跳过前必须核对副作用,不能只信 status 字段——status=succeeded 但 Note 未落库
    (如测试用 FakeCreateNote、或写入后回滚)时不应跳过,否则会漏掉真正的审批/执行。
    idempotency_key 与 write_tools.create_note 一致:agent:{session_id}:{tool_call_id}。
    用于恢复核对(planned 行带具体 tool_call_id,Note 在该 tool_call_id 名下)。
    """
    from app.models.note import Note  # 延迟导入,避免 tool_ops 与 models 循环依赖

    own = db is None
    db = db or SessionLocal()
    try:
        key = f"agent:{session_id}:{tool_call_id}"
        row = (
            db.query(Note)
            .filter(Note.user_id == user_id, Note.idempotency_key == key)
            .first()
        )
        return row is not None
    finally:
        if own:
            db.close()


def verify_note_by_id(user_id: str, note_id: str, db=None) -> bool:
    """按 note id 核对 Note 是否落库(业务级幂等跨 tool_call_id 用)。

    业务级 operation_id 是 args 级,跨 tool_call_id 重放时 Note 在首个 tool_call_id 名下,
    按 idempotency_key 核对会漏;按缓存结果里的 note id 核对,同一次业务操作的副作用统一可验。
    """
    from app.models.note import Note  # 延迟导入

    own = db is None
    db = db or SessionLocal()
    try:
        row = (
            db.query(Note)
            .filter(Note.user_id == user_id, Note.id == note_id)
            .first()
        )
        return row is not None
    finally:
        if own:
            db.close()


def list_planned_by_session(session_id: str, db=None) -> list:
    """列出会话内所有仍为 planned 的行(断流恢复时核对这些操作的副作用)。

    返回 [{operation_id, tool_call_id, tool_name, args_json}]。
    """
    own = db is None
    db = db or SessionLocal()
    try:
        rows = (
            db.query(AgentToolCall)
            .filter(
                AgentToolCall.session_id == session_id,
                AgentToolCall.status == STATUS_PLANNED,
            )
            .order_by(AgentToolCall.created_at.asc())
            .all()
        )
        return [
            {
                "operation_id": r.operation_id,
                "tool_call_id": r.tool_call_id,
                "tool_name": r.tool_name,
                "args_json": r.args_json,
            }
            for r in rows
        ]
    finally:
        if own:
            db.close()
