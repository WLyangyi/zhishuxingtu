"""双链关联表的写入小接口。

调用方仍负责维护 notes.linked_note_ids（回滚保险），这里只管关联表：
同一标题在正文出现多次会在 JSON 里留重复 id，但关联表主键需要去重。
"""

from typing import Iterable

from sqlalchemy.orm import Session

from app.models.note_link import NoteLink


def add_outgoing_links(db: Session, source_id: str, linked_ids: Iterable[str]) -> None:
    """追加出链（已存在的行跳过）。"""
    db.add_all([
        NoteLink(source_id=source_id, target_id=target_id)
        for target_id in dict.fromkeys(linked_ids)
    ])


def replace_outgoing_links(db: Session, source_id: str, linked_ids: Iterable[str]) -> None:
    """用新的出链集合整体替换旧集合（笔记正文改写时调用）。"""
    db.query(NoteLink).filter(NoteLink.source_id == source_id).delete(synchronize_session=False)
    add_outgoing_links(db, source_id, linked_ids)


def outgoing_links_by_source(db: Session, source_ids: Iterable[str]) -> dict:
    """一次查询取出一组来源笔记的出链，避免列表页逐篇 json.loads。"""
    ids = list(source_ids)
    if not ids:
        return {}
    result = {source_id: [] for source_id in ids}
    rows = db.query(NoteLink.source_id, NoteLink.target_id).filter(
        NoteLink.source_id.in_(ids)
    ).all()
    for source_id, target_id in rows:
        result.setdefault(source_id, []).append(target_id)
    return result
