# -*- coding: utf-8 -*-
"""三期3.4:断流恢复核对流程。

断流/重启后,execute_tool 已登记的 planned 行可能停留在 planned(执行未完成或
update_result 未跑)。恢复时按 operation_id 核对副作用是否已落地:
- 写工具(create_note):查 Note 是否已按 idempotency_key 落库,确认副作用;
  确认则把行补记为 succeeded(核对一致),未确认则标记 unknown 供重试/人工。
- 读工具:无副作用,标记 unknown(仅报告,不重执行)。

返回恢复核对报告,供路由层 SSE 展示与后续轮次幂等决策(operation_id 已成功则跳过重执行)。
"""
import json
from typing import Optional

from app.db.session import SessionLocal
from app.models.agent_session import AgentToolCall
from app.models.note import Note
from app.services.agent.tool_ops import (
    STATUS_SUCCEEDED,
    list_planned_by_session,
    query_result,
    update_result,
)

# 有副作用需核对的工具(写工具)
WRITE_TOOLS = {"create_note"}


def _note_idempotency_key(session_id: str, tool_call_id: str) -> str:
    """与 write_tools.create_note 的幂等键一致:agent:{session_id}:{tool_call_id}。"""
    return f"agent:{session_id}:{tool_call_id}"


def reconcile_recovery(session_id: str, user_id: str, db=None) -> dict:
    """核对会话内所有 planned 行,返回恢复报告。

    返回:
    {
        "items": [{operation_id, tool_name, tool_call_id, status, action, confirmed}],
        "confirmed": int, "unknown": int, "total": int, "has_pending": bool,
    }
    action: confirmed(副作用已落地,行补记 succeeded)/unknown(副作用未确认,需重试或人工)
    """
    own = db is None
    db = db or SessionLocal()
    try:
        planned = list_planned_by_session(session_id, db=db)
        items = []
        confirmed = unknown = 0
        for p in planned:
            op_id = p["operation_id"]
            tool_name = p["tool_name"] or ""
            tool_call_id = p["tool_call_id"] or ""
            res = query_result(session_id, op_id, db=db)
            status = (res or {}).get("status", "planned")
            action = "unknown"
            side_confirmed = False
            if tool_name in WRITE_TOOLS:
                key = _note_idempotency_key(session_id, tool_call_id)
                note = (
                    db.query(Note)
                    .filter(Note.user_id == user_id, Note.idempotency_key == key)
                    .first()
                )
                if note is not None:
                    side_confirmed = True
                    action = "confirmed"
                    # 副作用已落地,补记行 succeeded(核对一致,后续重放按 operation_id 幂等跳过)
                    try:
                        update_result(
                            session_id,
                            tool_call_id,
                            STATUS_SUCCEEDED,
                            json.dumps({"id": note.id, "recovered": True}, ensure_ascii=False),
                            0,
                            db=db,
                        )
                    except Exception:  # noqa: BLE001 补记失败不阻断核对
                        pass
            if action == "confirmed":
                confirmed += 1
            else:
                unknown += 1
            items.append(
                {
                    "operation_id": op_id,
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "status": status,
                    "action": action,
                    "confirmed": side_confirmed,
                }
            )
        return {
            "items": items,
            "confirmed": confirmed,
            "unknown": unknown,
            "total": len(items),
            "has_pending": bool(items),
        }
    finally:
        if own:
            db.close()
