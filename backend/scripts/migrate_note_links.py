"""P1-1 迁移:把 notes.linked_note_ids(JSON Text) 回填到 note_links 关联表。

幂等:已存在的 (source_id, target_id) 直接跳过;坏 JSON、非字符串 id、悬空 target 跳过。
运行方式(backend 目录下):
  .venv\\Scripts\\python.exe scripts\\migrate_note_links.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.note import Note  # noqa: E402
from app.models.note_link import NoteLink  # noqa: E402


def migrate_note_links(db):
    """对给定 Session 执行迁移,返回统计字典。供脚本与回归测试共用。"""
    NoteLink.__table__.create(bind=db.get_bind(), checkfirst=True)
    stats = {"inserted": 0, "skipped_bad_json": 0, "skipped_missing_target": 0}

    notes = db.query(Note).all()
    note_ids = {note.id for note in notes}
    for note in notes:
        raw = note.linked_note_ids
        if not raw:
            continue
        try:
            linked_ids = json.loads(raw)
        except (TypeError, ValueError):
            stats["skipped_bad_json"] += 1
            continue
        if not isinstance(linked_ids, list):
            stats["skipped_bad_json"] += 1
            continue

        existing = {
            row[0] for row in db.query(NoteLink.target_id).filter_by(source_id=note.id).all()
        }
        new_rows = []
        for target_id in dict.fromkeys(linked_ids):
            if not isinstance(target_id, str):
                continue
            if target_id not in note_ids:
                stats["skipped_missing_target"] += 1
                continue
            if target_id not in existing:
                new_rows.append({"source_id": note.id, "target_id": target_id})
                existing.add(target_id)

        if new_rows:
            db.execute(NoteLink.__table__.insert(), new_rows)
            stats["inserted"] += len(new_rows)

    return stats


if __name__ == "__main__":
    from app.db.session import SessionLocal  # noqa: E402

    db = SessionLocal()
    try:
        result = migrate_note_links(db)
        db.commit()
        print(
            f"迁移完成:新增 {result['inserted']} 条,坏 JSON {result['skipped_bad_json']} 篇,"
            f"悬空目标 {result['skipped_missing_target']} 个"
        )
    finally:
        db.close()
