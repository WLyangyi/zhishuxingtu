import json

from langchain_core.tools import tool

SNIPPET_LEN = 300
NOTE_BODY_LEN = 2000


@tool
def search_notes(query: str, top_k: int = 5) -> str:
    """检索个人知识库中的相关笔记(混合检索:向量语义 + 关键词 BM25 + 重排序)。

    返回 JSON 数组,每项含 id / title / snippet(≤300 字)。适合回答需要引用笔记的问题。
    """
    from app.api.routes.search import hybrid_search_notes
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        notes = hybrid_search_notes(query, db, k=top_k, use_reranker=True)
        out = []
        for n, score in notes:
            content = (n.content or "")[:SNIPPET_LEN]
            out.append({"id": n.id, "title": (n.title or "")[:100], "snippet": content})
        return json.dumps(out, ensure_ascii=False)
    finally:
        db.close()


@tool
def get_note(note_id: str) -> str:
    """按 id 获取单篇笔记的完整内容(前 2000 字,超长标注'已截断')。

    note_id 通常来自 search_notes 返回的 id 字段。
    """
    from app.db.session import SessionLocal
    from app.models.note import Note

    db = SessionLocal()
    try:
        n = db.query(Note).filter(Note.id == note_id).first()
        if not n:
            return json.dumps({"error": "未找到该笔记"}, ensure_ascii=False)
        content = n.content or ""
        truncated = len(content) > NOTE_BODY_LEN
        body = content[:NOTE_BODY_LEN] + ("\n[已截断,可追问摘要]" if truncated else "")
        return json.dumps({"id": n.id, "title": n.title, "content": body}, ensure_ascii=False)
    finally:
        db.close()
