# -*- coding: utf-8 -*-
"""P3 后端最小配套：观测台聚合口径 + 阅读记录幂等/隔离。"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.category import Category
from app.models.folder import Folder
from app.models.note import Note
from app.models.note_view import NoteView
from app.models.tag import Tag
from app.models.user import User
from app.queries.home import build_home_overview, record_note_view


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def seeded(db):
    db.add_all(
        [
            User(id="u1", username="alice", password_hash="x"),
            User(id="u2", username="bob", password_hash="x"),
        ]
    )
    db.add(Category(id="c1", name="工作"))
    db.flush()
    db.add(Folder(id="f1", name="AI", category_id="c1", user_id="u1", level=0))
    db.flush()

    rag = Tag(id="t1", name="RAG")
    agent = Tag(id="t2", name="Agent")

    n1 = Note(
        id="n1",
        title="Agent 三查反思",
        content="hello world",
        user_id="u1",
        folder_id="f1",
        linked_note_ids=json.dumps(["n2", "n2"]),
        updated_at=datetime(2026, 11, 17, 10, 0, 0),
    )
    n2 = Note(
        id="n2",
        title="向量检索实验",
        content="中文 内容\n第二行",
        user_id="u1",
        folder_id="f1",
        updated_at=datetime(2026, 11, 17, 9, 0, 0),
    )
    n3 = Note(
        id="n3",
        title="空内容",
        content="   ",
        user_id="u2",
        updated_at=datetime(2026, 11, 17, 8, 0, 0),
    )
    n1.tags = [rag, agent]
    n2.tags = [rag]
    db.add_all([n1, n2, n3])
    db.commit()
    return {"u1": "u1", "u2": "u2"}


def test_empty_library_returns_zeroed_overview(db):
    overview = build_home_overview(db, "u1")

    assert overview["stats"] == {
        "notes": 0,
        "tags": 0,
        "folders": 0,
        "categories": 0,
        "words": 0,
        "links": 0,
    }
    assert overview["recent_notes"] == []
    assert overview["recent_reads"] == []
    assert overview["top_tags"] == []
    assert overview["areas"] == []


def test_overview_stats_and_ordering(db, seeded):
    overview = build_home_overview(db, seeded["u1"])

    assert overview["stats"]["notes"] == 3
    assert overview["stats"]["tags"] == 2
    assert overview["stats"]["folders"] == 1
    assert overview["stats"]["categories"] == 1
    # hello world = 10，中文内容+第二行 = 7，空内容 = 0
    assert overview["stats"]["words"] == 17
    # n1 的 ["n2","n2"] 去重后算 1 条链接
    assert overview["stats"]["links"] == 1

    assert [item["id"] for item in overview["recent_notes"]][:2] == ["n1", "n2"]
    assert overview["recent_notes"][0]["excerpt"] == "hello world"
    assert overview["recent_notes"][0]["category_id"] == "c1"
    assert overview["recent_notes"][0]["link_count"] == 1

    assert overview["top_tags"][0] == {"id": "t1", "name": "RAG", "note_count": 2}
    assert overview["areas"] == [{"id": "c1", "name": "工作", "note_count": 2}]


def test_record_view_upserts_single_row(db, seeded):
    record_note_view(db, seeded["u1"], "n1")
    record_note_view(db, seeded["u1"], "n1")

    rows = db.query(NoteView).filter_by(user_id="u1", note_id="n1").all()
    assert len(rows) == 1
    assert rows[0].viewed_at is not None


def test_recent_reads_are_per_user_and_ordered(db, seeded):
    record_note_view(db, seeded["u1"], "n1")
    record_note_view(db, seeded["u1"], "n2")

    overview = build_home_overview(db, seeded["u1"])
    assert [item["note_id"] for item in overview["recent_reads"]] == ["n2", "n1"]
    assert overview["recent_reads"][0]["title"] == "向量检索实验"
    assert overview["recent_reads"][0]["excerpt"].startswith("中文 内容")

    other = build_home_overview(db, seeded["u2"])
    assert other["recent_reads"] == []


def test_record_view_rejects_missing_note(db, seeded):
    with pytest.raises(LookupError):
        record_note_view(db, seeded["u1"], "not-exists")
