import json

from langchain_core.tools import tool


@tool
def get_graph_neighbors(note_id: str, depth: int = 1) -> str:
    """查询知识图谱中某笔记的邻居节点(基于 [[双向链接]] 的一跳出边 + 入边)。

    返回 JSON,含 neighbors 列表(id/title/relation)。用于理解笔记之间的关联。
    """
    from app.db.session import SessionLocal
    from app.models.note import Note

    db = SessionLocal()
    try:
        note = db.query(Note).filter(Note.id == note_id).first()
        if not note:
            return json.dumps({"error": "未找到该笔记", "neighbors": []}, ensure_ascii=False)

        # 出边:linked_note_ids
        out_ids = []
        try:
            out_ids = json.loads(note.linked_note_ids) if note.linked_note_ids else []
        except Exception:
            out_ids = []

        neighbors = []
        for nid in out_ids:
            n = db.query(Note).filter(Note.id == nid).first()
            if n:
                neighbors.append({"id": n.id, "title": n.title, "relation": "links_to"})

        # 入边:被哪些笔记链接
        backlinks = (
            db.query(Note)
            .filter(Note.linked_note_ids.contains(f'"{note_id}"'))
            .all()
        )
        for n in backlinks:
            if n.id == note_id:
                continue
            neighbors.append({"id": n.id, "title": n.title, "relation": "linked_by"})

        return json.dumps({"note_id": note_id, "neighbors": neighbors[:20]}, ensure_ascii=False)
    finally:
        db.close()
