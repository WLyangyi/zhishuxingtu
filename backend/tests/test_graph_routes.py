# -*- coding: utf-8 -*-
"""P1-4:graph 路由回归——节点/边数量、局部图边界、悬空 id、500 篇规模。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.routes.graph import router as graph_router
from app.db.base import Base
from app.db.session import get_db
from app.models.folder import Folder
from app.models.note import Note
from app.models.note_link import NoteLink
from app.models.tag import Tag
from app.models.user import User


@pytest.fixture()
def api():
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

    app = FastAPI()
    app.include_router(graph_router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    with TestClient(app) as client:
        yield client, db

    db.close()
    engine.dispose()


def _note(db, note_id, title, user_id="u1", folder_id=None, tags=()):
    note = Note(id=note_id, title=title, user_id=user_id, folder_id=folder_id, content="")
    if tags:
        note.tags = list(tags)
    db.add(note)
    db.commit()
    return note


def _edge_set(payload, edge_type=None):
    return {
        (edge["source"], edge["target"])
        for edge in payload["edges"]
        if edge_type is None or edge["type"] == edge_type
    }


def test_global_graph_counts_nodes_and_edges(api):
    client, db = api
    folder = Folder(id="f1", name="工作", user_id="u1", level=0)
    tag = Tag(id="t1", name="RAG")
    db.add_all([folder, tag])
    db.commit()
    _note(db, "n1", "笔记一", folder_id="f1", tags=(tag,))
    _note(db, "n2", "笔记二")
    db.add(NoteLink(source_id="n1", target_id="n2"))
    db.commit()

    payload = client.get("/api/graph/global").json()["data"]

    counts = {}
    for node in payload["nodes"]:
        counts[node["type"]] = counts.get(node["type"], 0) + 1
    assert counts == {"folder": 1, "tag": 1, "note": 2}
    assert len(payload["edges"]) == 3
    assert ("f1", "n1") in _edge_set(payload, "contains")
    assert ("n1", "t1") in _edge_set(payload, "has_tag")
    assert _edge_set(payload, "links_to") == {("n1", "n2")}


def test_global_graph_excludes_other_user_notes(api):
    client, db = api
    _note(db, "mine", "我的笔记")
    _note(db, "theirs", "别人的笔记", user_id="u2")
    db.add(NoteLink(source_id="mine", target_id="theirs"))
    db.commit()

    payload = client.get("/api/graph/global").json()["data"]

    assert {node["id"] for node in payload["nodes"]} == {"mine"}
    assert payload["edges"] == []


def test_local_graph_without_links_has_only_current_note(api):
    client, db = api
    _note(db, "alone", "孤立笔记")

    payload = client.get("/api/graph/local/alone").json()["data"]

    assert [node["id"] for node in payload["nodes"]] == ["alone"]
    assert payload["edges"] == []


def test_local_graph_includes_outgoing_and_backlinks(api):
    client, db = api
    _note(db, "center", "中心")
    _note(db, "out", "出链目标")
    _note(db, "in", "反链来源")
    db.add_all([
        NoteLink(source_id="center", target_id="out"),
        NoteLink(source_id="in", target_id="center"),
    ])
    db.commit()

    payload = client.get("/api/graph/local/center").json()["data"]

    assert {node["id"] for node in payload["nodes"]} == {"center", "out", "in"}
    assert _edge_set(payload, "links_to") == {("center", "out"), ("in", "center")}


def test_local_graph_ignores_dangling_link_target(api):
    client, db = api
    _note(db, "center", "中心")
    db.add(NoteLink(source_id="center", target_id="ghost"))
    db.commit()

    payload = client.get("/api/graph/local/center").json()["data"]

    assert [node["id"] for node in payload["nodes"]] == ["center"]
    assert payload["edges"] == []


def test_global_graph_500_notes_smoke(api):
    client, db = api
    ids = [f"n{i}" for i in range(500)]
    db.add_all([Note(id=note_id, title=note_id, user_id="u1", content="") for note_id in ids])
    db.add_all([
        NoteLink(source_id=note_id, target_id=ids[(i + 1) % 500])
        for i, note_id in enumerate(ids)
    ])
    db.commit()

    start = time.perf_counter()
    response = client.get("/api/graph/global")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    data = response.json()["data"]
    assert sum(node["type"] == "note" for node in data["nodes"]) == 500
    assert len(_edge_set(data, "links_to")) == 500
    assert elapsed < 5


def test_global_graph_returns_304_when_etag_matches(api):
    client, db = api
    _note(db, "n1", "笔记一")

    first = client.get("/api/graph/global")
    assert first.status_code == 200
    etag = first.headers["etag"]

    second = client.get("/api/graph/global", headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.content == b""


def test_global_graph_etag_changes_when_note_updated(api):
    client, db = api
    note = _note(db, "n1", "笔记一")
    etag = client.get("/api/graph/global").headers["etag"]

    note.title = "改名了"
    db.commit()

    response = client.get("/api/graph/global", headers={"If-None-Match": etag})
    assert response.status_code == 200
    assert response.headers["etag"] != etag
