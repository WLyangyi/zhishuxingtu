# -*- coding: utf-8 -*-
"""观测台首页聚合与阅读记录（P3）。

独立查询层：不依赖 app.services 的重初始化。
分层约定：路由只做参数/异常映射，聚合口径全部在这里，便于 pytest 直接验证。
"""
import json
import re
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.folder import Folder
from app.models.note import Note, note_tags
from app.models.note_view import NoteView
from app.models.tag import Tag


def _excerpt(content: str | None, limit: int = 80) -> str:
    text = re.sub(r"\s+", " ", content or "").strip()
    return text[:limit]


def _word_count(content: str | None) -> int:
    return len(re.sub(r"\s+", "", content or ""))


def _link_count(raw: str | None) -> int:
    try:
        values = json.loads(raw) if raw else []
    except (TypeError, ValueError):
        return 0
    if not isinstance(values, list):
        return 0
    return len({str(value) for value in values})


def build_home_overview(db: Session, user_id: str) -> dict:
    notes = db.query(Note).all()

    stats = {
        "notes": len(notes),
        "tags": db.query(func.count(Tag.id)).scalar() or 0,
        "folders": db.query(func.count(Folder.id)).scalar() or 0,
        "categories": db.query(func.count(Category.id)).scalar() or 0,
        "words": sum(_word_count(note.content) for note in notes),
        "links": sum(_link_count(note.linked_note_ids) for note in notes),
    }

    recent_notes = [
        {
            "id": note.id,
            "title": note.title,
            "excerpt": _excerpt(note.content),
            "updated_at": note.updated_at,
            "folder_id": note.folder_id,
            "category_id": note.folder.category_id if note.folder else None,
            "link_count": _link_count(note.linked_note_ids),
        }
        for note in db.query(Note).order_by(Note.updated_at.desc()).limit(5).all()
    ]

    read_rows = (
        db.query(NoteView, Note)
        .join(Note, Note.id == NoteView.note_id)
        .filter(NoteView.user_id == user_id)
        .order_by(NoteView.viewed_at.desc())
        .limit(5)
        .all()
    )
    recent_reads = [
        {
            "note_id": note.id,
            "title": note.title,
            "excerpt": _excerpt(note.content),
            "viewed_at": view.viewed_at,
        }
        for view, note in read_rows
    ]

    tag_rows = (
        db.query(
            Tag.id,
            Tag.name,
            func.count(note_tags.c.note_id).label("note_count"),
        )
        .join(note_tags, note_tags.c.tag_id == Tag.id)
        .group_by(Tag.id, Tag.name)
        .order_by(func.count(note_tags.c.note_id).desc(), Tag.name.asc())
        .limit(6)
        .all()
    )
    top_tags = [
        {"id": row.id, "name": row.name, "note_count": row.note_count} for row in tag_rows
    ]

    area_rows = (
        db.query(
            Category.id,
            Category.name,
            func.count(Note.id).label("note_count"),
        )
        .outerjoin(Folder, Folder.category_id == Category.id)
        .outerjoin(Note, Note.folder_id == Folder.id)
        .group_by(Category.id, Category.name, Category.sort_order)
        .order_by(Category.sort_order.asc(), Category.name.asc())
        .all()
    )
    areas = [
        {"id": row.id, "name": row.name, "note_count": row.note_count} for row in area_rows
    ]

    return {
        "stats": stats,
        "recent_notes": recent_notes,
        "recent_reads": recent_reads,
        "top_tags": top_tags,
        "areas": areas,
    }


def record_note_view(db: Session, user_id: str, note_id: str) -> None:
    if db.get(Note, note_id) is None:
        raise LookupError(f"note not found: {note_id}")

    now = datetime.now(timezone.utc)
    view = db.query(NoteView).filter_by(user_id=user_id, note_id=note_id).first()
    if view is not None:
        view.viewed_at = now
    else:
        db.add(NoteView(user_id=user_id, note_id=note_id, viewed_at=now))
    db.commit()
