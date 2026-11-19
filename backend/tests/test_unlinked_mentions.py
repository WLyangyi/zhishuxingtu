# -*- coding: utf-8 -*-
"""P2-4 补充:GET /api/notes/{id}/unlinked-mentions 后端预计算未链接提及。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.routes.notes import router as notes_router
from app.db.base import Base
from app.db.session import get_db
from app.models.note import Note
from app.models.user import User


@pytest.fixture()
def api(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()

    user = User(id="u1", username="tester", password_hash="x")
    other = User(id="u2", username="other", password_hash="x")
    db.add_all([user, other])
    db.commit()

    monkeypatch.setattr("app.api.routes.notes.get_vector_store_adapter", lambda: None)
    monkeypatch.setattr("app.api.routes.notes.get_vector_store", lambda: None)

    # n1 正文:提到 n2(未建链)、n4(已 [[ ]] 建链)、n3(别人的笔记)
    notes = [
        Note(id="n1", title="当前笔记", user_id="u1", content="提到了 RAG 混合检索 和 [[Agent 记忆]]，还有 别人的笔记"),
        Note(id="n2", title="RAG 混合检索", user_id="u1", content=""),
        Note(id="n3", title="别人的笔记", user_id="u2", content=""),
        Note(id="n4", title="Agent 记忆", user_id="u1", content=""),
    ]
    for note in notes:
        db.add(note)
    db.commit()

    app = FastAPI()
    app.include_router(notes_router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    with TestClient(app) as client:
        yield client, db

    db.close()
    engine.dispose()


def test_unlinked_mentions_excludes_linked_and_other_users(api):
    client, _ = api
    resp = client.get("/api/notes/n1/unlinked-mentions")
    assert resp.status_code == 200
    items = resp.json()["data"]
    # 只返回同用户、纯文本提及、未写成 [[ ]] 的笔记
    assert [item["id"] for item in items] == ["n2"]
    assert items[0]["title"] == "RAG 混合检索"


def test_unlinked_mentions_404_for_missing_note(api):
    client, _ = api
    assert client.get("/api/notes/nope/unlinked-mentions").status_code == 404


def test_unlinked_mentions_empty_when_all_linked(api):
    client, db = api
    note = db.query(Note).filter(Note.id == "n1").first()
    note.content = "全部都 [[RAG 混合检索]] 和 [[Agent 记忆]] 建链了"
    db.commit()
    resp = client.get("/api/notes/n1/unlinked-mentions")
    assert resp.json()["data"] == []
