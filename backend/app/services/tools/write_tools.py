import json
import logging
from typing import Any, Optional

from langchain_core.tools import tool
from sqlalchemy.exc import IntegrityError

from app.services.tools.context import get_tool_context

logger = logging.getLogger(__name__)


def _idempotent_payload(note: Any) -> str:
    """重放命中已有笔记时返回同一份结构,并显式标记 idempotent_replay。"""
    return json.dumps(
        {
            "id": note.id,
            "title": note.title,
            "folder_id": note.folder_id,
            "idempotent_replay": True,
        },
        ensure_ascii=False,
    )


@tool
def create_note(title: str, content: str, folder_id: Optional[str] = None) -> str:
    """创建一篇知识库笔记。该写操作必须经人工审批后才会真正执行。

    返回 JSON，包含新笔记 id/title/folder_id；失败时返回 error。
    """
    from app.api.routes.notes import resolve_links
    from app.db.session import SessionLocal
    from app.models.folder import Folder
    from app.models.note import Note

    ctx = get_tool_context()
    if not ctx or not ctx.user_id:
        return json.dumps({"error": "缺少用户上下文，拒绝创建笔记"}, ensure_ascii=False)
    if not title.strip():
        return json.dumps({"error": "笔记标题不能为空"}, ensure_ascii=False)

    db = SessionLocal()
    # 幂等键:同一 session 的同一个 tool_call 被重放(resume/重试)时复用已有笔记。
    # MCP 直调没有 tool_call_id,退化为无幂等,保持原行为。
    idem_key = (
        f"agent:{ctx.session_id}:{ctx.tool_call_id}"
        if ctx.session_id and ctx.tool_call_id
        else None
    )
    try:
        if idem_key:
            existing = (
                db.query(Note)
                .filter(Note.user_id == ctx.user_id, Note.idempotency_key == idem_key)
                .first()
            )
            if existing:
                return _idempotent_payload(existing)

        if folder_id:
            folder = db.query(Folder).filter(Folder.id == folder_id).first()
            if not folder or (folder.user_id and folder.user_id != ctx.user_id):
                return json.dumps({"error": "目录不存在或无权使用"}, ensure_ascii=False)

        linked_ids = resolve_links(db, content)
        note = Note(
            title=title.strip()[:500],
            content=content,
            folder_id=folder_id,
            user_id=ctx.user_id,
            linked_note_ids=json.dumps(linked_ids, ensure_ascii=False),
            idempotency_key=idem_key,
        )
        db.add(note)
        db.commit()
        db.refresh(note)

        # 与普通笔记创建保持一致；embedding 不可用时不影响写入主流程。
        try:
            from app.services.embedding_service import embedding_service
            from app.services.vector_store_adapter import get_vector_store_adapter

            vector_store = get_vector_store_adapter()
            if vector_store and embedding_service.available and note.content:
                chunks, vectors = embedding_service.embed_chunks(note.id, note.title, note.content)
                if chunks and len(vectors) > 0:
                    vector_store.add_note_chunks(note.id, chunks, vectors)
                    vector_store.save()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to index agent-created note %s: %s", note.id, exc)

        # 关键词索引同步追加，保证新笔记在当前进程内立刻可被检索。
        try:
            from app.services.bm25_service import get_bm25_service

            bm25 = get_bm25_service()
            if bm25.is_ready:
                bm25.add_document(note.id, note.title or "", note.content or "")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to update BM25 for agent-created note %s: %s", note.id, exc)

        return json.dumps(
            {"id": note.id, "title": note.title, "folder_id": note.folder_id},
            ensure_ascii=False,
        )
    except IntegrityError:
        # 并发重放:唯一索引挡住第二次写入,回查已落库的那篇,保持幂等语义。
        db.rollback()
        existing = (
            db.query(Note)
            .filter(Note.user_id == ctx.user_id, Note.idempotency_key == idem_key)
            .first()
            if idem_key
            else None
        )
        if existing:
            return _idempotent_payload(existing)
        return json.dumps(
            {"error": "唯一约束冲突,但未找到对应的已存在笔记"}, ensure_ascii=False
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("Agent create_note failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    finally:
        db.close()
