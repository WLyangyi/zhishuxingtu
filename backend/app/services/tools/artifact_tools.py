import json

from langchain_core.tools import tool

from app.services.tools.context import get_tool_context

DEFAULT_LIMIT = 2000


@tool
def read_tool_artifact(artifact_id: str, offset: int = 0, limit: int = DEFAULT_LIMIT) -> str:
    """按 id 取回被压缩的大工具结果原文(分页)。

    当某次工具结果提示"已存档 artifact_id=..."时,用该 id 读取原始内容。
    offset 为起始字符,limit 为本次最多返回的字符数(默认 2000)。
    """
    from app.db.session import SessionLocal
    from app.models.agent_session import AgentToolArtifact

    ctx = get_tool_context()
    session_id = getattr(ctx, "session_id", "") or ""
    if not session_id:
        return json.dumps({"error": "缺少会话上下文,无法读取工具结果存档"}, ensure_ascii=False)

    db = SessionLocal()
    try:
        # 会话隔离:只能读本会话自己的存档,避免跨会话/跨用户越权读取
        row = (
            db.query(AgentToolArtifact)
            .filter(
                AgentToolArtifact.id == artifact_id,
                AgentToolArtifact.session_id == session_id,
            )
            .first()
        )
        if not row:
            return json.dumps({"error": "未找到该工具结果存档(或不属于当前会话)"}, ensure_ascii=False)
        start = max(0, int(offset or 0))
        take = max(1, min(int(limit or DEFAULT_LIMIT), 8000))
        body = (row.content or "")[start : start + take]
        return json.dumps(
            {
                "artifact_id": row.id,
                "tool_name": row.tool_name,
                "total_length": row.length or len(row.content or ""),
                "offset": start,
                "returned": len(body),
                "truncated": start + len(body) < (row.length or len(row.content or "")),
                "content": body,
            },
            ensure_ascii=False,
        )
    finally:
        db.close()
