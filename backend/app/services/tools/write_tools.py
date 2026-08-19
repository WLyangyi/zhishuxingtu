import json
import logging
from typing import Optional

from langchain_core.tools import tool

from app.services.tools.context import get_tool_context

logger = logging.getLogger(__name__)


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
    try:
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
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to index agent-created note %s: %s", note.id, exc)

        return json.dumps(
            {"id": note.id, "title": note.title, "folder_id": note.folder_id},
            ensure_ascii=False,
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("Agent create_note failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    finally:
        db.close()
