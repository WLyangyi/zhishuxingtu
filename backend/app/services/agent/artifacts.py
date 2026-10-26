# -*- coding: utf-8 -*-
"""Phase 4:大工具结果 offload + 可恢复压缩。

检索或取全文一次可能返回上万字。原样塞进 ToolMessage 后,消息会进 checkpoint,
并在后续每一轮里作为历史上下文重新发给模型——单轮多跳就等于重复计费,
多轮会话则一路滚雪球。

所以超过阈值的结果:全文落到 agent_tool_artifacts,消息里只留结构化压缩预览 +
artifact_id;模型需要细节时再调 read_tool_artifact 取回(可恢复,不是单向截断)。
"""
import uuid
from typing import Any, Dict, List, Optional

PREVIEW_HEAD = 1200
PREVIEW_TAIL = 400
PREVIEW_ITEMS = 6
SNIPPET_KEEP = 200
NOTE_BODY_KEEP = 1200


def artifact_id(session_id: str, tool_call_id: str) -> str:
    """确定性 id:同一会话同一 tool_call 重放只会得到同一行(与工具审计同一口径)。"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{session_id}/{tool_call_id}"))


def _shrink_json_list(result: str) -> Optional[str]:
    """检索结果是 [{id,title,snippet}]:按字段投影压缩,比硬截断可读得多。"""
    import json

    try:
        data = json.loads(result)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, list) or not data:
        return None
    compact: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            return None
        slim = {k: v for k, v in item.items() if k in ("id", "title", "score", "updated_at")}
        if "snippet" in item:
            slim["snippet"] = str(item.get("snippet") or "")[:SNIPPET_KEEP]
        if "content" in item:
            slim["content"] = str(item.get("content") or "")[:NOTE_BODY_KEEP]
        compact.append(slim)
    if len(compact) > PREVIEW_ITEMS:
        # 条目本身已很精简(如 20 条短检索结果)时,字段投影省不下多少,
        # 改按条数截断,保证预览仍是可解析的 JSON 而不是被拦腰砍断的文本。
        dropped = len(compact) - PREVIEW_ITEMS
        compact = compact[:PREVIEW_ITEMS]
        compact.append({"_dropped_items": dropped})
    return json.dumps(compact, ensure_ascii=False)


def _shrink_json_dict(result: str) -> Optional[str]:
    """单篇笔记结果 {id,title,content}:保住标题与前段正文,长尾交给 artifact。"""
    import json

    try:
        data = json.loads(result)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict) or not data:
        return None
    slim: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str) and len(value) > NOTE_BODY_KEEP:
            slim[key] = value[:NOTE_BODY_KEEP]
        else:
            slim[key] = value
    return json.dumps(slim, ensure_ascii=False)


def compress_result(result: str) -> str:
    """把超阈值结果压成"可继续推理"的预览(原文由调用方负责落盘)。"""
    compressed = _shrink_json_list(result) or _shrink_json_dict(result)
    if compressed is None or len(compressed) >= len(result):
        # 非结构化大文本:头 + 尾,中间省略,避免把关键结论(常在末尾)一起砍掉
        compressed = result[:PREVIEW_HEAD] + "\n…[中间省略]…\n" + result[-PREVIEW_TAIL:]
    return compressed


def save_artifact(
    session_id: str, tool_call_id: str, tool_name: str, content: str
) -> Optional[str]:
    """落库并返回 artifact_id;任何异常都返回 None(offload 失败不能拖垮主链路)。"""
    if not session_id or not tool_call_id:
        return None
    try:
        from app.db.session import SessionLocal
        from app.models.agent_session import AgentToolArtifact

        record_id = artifact_id(session_id, tool_call_id)
        db = SessionLocal()
        try:
            exists = db.query(AgentToolArtifact).filter(
                AgentToolArtifact.id == record_id
            ).first()
            if exists:
                return record_id
            db.add(
                AgentToolArtifact(
                    id=record_id,
                    session_id=session_id,
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    content=content,
                    length=len(content),
                )
            )
            db.commit()
            return record_id
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        print(f"[artifact] 保存失败,退回完整结果:{exc}")
        return None
