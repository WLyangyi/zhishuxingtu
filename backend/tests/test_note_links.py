# -*- coding: utf-8 -*-
"""P1-1:linked_note_ids JSON Text → note_links 关联表。

行为通过笔记/图谱 HTTP 接口验证；关联表是数据层对其它服务的公开契约，
因此在必要时直接断言行集合，而不是断言某个内部 helper 的返回值。
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.routes.graph import router as graph_router
from app.api.routes.notes import router as notes_router
from app.db.base import Base
from app.db.session import get_db
from app.models.note import Note
from app.models.note_link import NoteLink
from app.models.user import User


@pytest.fixture()
def api(monkeypatch):
    # TestClient 在线程池里跑路由，必须用 StaticPool 共享同一个内存库连接，
    # 否则每个线程拿到空库，表现为 "no such table"。
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)
    db = session()

    user = User(id="u1", username="tester", password_hash="x")
    db.add(user)
    db.commit()

    # 向量化/索引是外部系统边界，冒烟不写真实 FAISS
    monkeypatch.setattr("app.api.routes.notes.get_vector_store_adapter", lambda: None)
    monkeypatch.setattr("app.api.routes.notes.get_vector_store", lambda: None)

    app = FastAPI()
    app.include_router(notes_router, prefix="/api")
    app.include_router(graph_router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    with TestClient(app) as client:
        yield client, db

    db.close()
    engine.dispose()


def _note(db, note_id, title, linked=None):
    note = Note(
        id=note_id,
        title=title,
        content="",
        user_id="u1",
        linked_note_ids=json.dumps(linked) if linked is not None else None,
    )
    db.add(note)
    db.commit()
    return note


def test_create_note_writes_outgoing_links_to_note_links(api):
    client, db = api
    _note(db, "target", "目标笔记")

    response = client.post("/api/notes", json={
        "title": "源笔记",
        "content": "正文里引用 [[目标笔记]]",
    })

    assert response.status_code == 200
    rows = db.query(NoteLink).filter(NoteLink.source_id == response.json()["data"]["id"]).all()
    assert [(row.source_id, row.target_id) for row in rows] == [
        (response.json()["data"]["id"], "target")
    ]


def test_update_note_replaces_outgoing_links(api):
    client, db = api
    _note(db, "old-target", "旧目标")
    _note(db, "new-target", "新目标")
    source_id = client.post("/api/notes", json={
        "title": "源笔记",
        "content": "引用 [[旧目标]]",
    }).json()["data"]["id"]

    response = client.put(f"/api/notes/{source_id}", json={
        "content": "改写为 [[新目标]]",
    })

    assert response.status_code == 200
    rows = db.query(NoteLink).filter(NoteLink.source_id == source_id).all()
    assert {row.target_id for row in rows} == {"new-target"}
    assert response.json()["data"]["linked_note_ids"] == ["new-target"]


def test_delete_note_removes_dangling_links(api):
    client, db = api
    _note(db, "target", "目标笔记")
    source_id = client.post("/api/notes", json={
        "title": "源笔记",
        "content": "引用 [[目标笔记]]",
    }).json()["data"]["id"]
    _note(db, "other-source", "另一来源", linked=[source_id])

    response = client.delete(f"/api/notes/{source_id}")

    assert response.status_code == 200
    remaining = db.query(NoteLink).all()
    assert all(row.source_id != source_id and row.target_id != source_id for row in remaining)


def test_agent_create_note_also_writes_outgoing_links(api, monkeypatch):
    """Agent 的 create_note 工具绕过 notes 路由，也必须维护关联表。"""
    client, db = api
    _note(db, "target", "目标笔记")

    from app.db.session import SessionLocal as real_session_local
    from app.services.tools.context import ToolContext, set_tool_context, reset_tool_context
    from app.services.tools.write_tools import create_note

    monkeypatch.setattr("app.db.session.SessionLocal", lambda: db)
    monkeypatch.setattr(
        "app.services.vector_store_adapter.get_vector_store_adapter", lambda: None
    )
    token = set_tool_context(ToolContext(user_id="u1", session_id="s1"))
    try:
        payload = create_note.invoke({
            "title": "Agent 笔记",
            "content": "引用 [[目标笔记]]",
        })
    finally:
        reset_tool_context(token)
        monkeypatch.setattr("app.db.session.SessionLocal", real_session_local)

    source_id = json.loads(payload)["id"]
    assert db.query(NoteLink).filter_by(source_id=source_id, target_id="target").count() == 1


def test_backlinks_come_from_link_table_not_json_scan(api):
    """JSON 里残留的旧出链不再被当成反链；只有关联表里的行算数。"""
    client, db = api
    _note(db, "target", "目标")
    _note(db, "legacy-json-only", "仅 JSON 出链", linked=["target"])
    proper_id = client.post("/api/notes", json={
        "title": "已迁移来源",
        "content": "引用 [[目标]]",
    }).json()["data"]["id"]

    response = client.get("/api/notes/target/backlinks")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [proper_id]

    empty = client.get("/api/notes/legacy-json-only/backlinks")
    assert empty.json()["data"] == []


def test_global_graph_edges_come_from_link_table(api):
    client, db = api
    _note(db, "target", "目标")
    _note(db, "legacy-json-only", "仅 JSON 出链", linked=["target"])
    proper_id = client.post("/api/notes", json={
        "title": "已迁移来源",
        "content": "引用 [[目标]]",
    }).json()["data"]["id"]
    db.add(NoteLink(source_id="legacy-json-only", target_id="ghost"))
    db.commit()

    response = client.get("/api/graph/global")

    assert response.status_code == 200
    links = {
        (edge["source"], edge["target"])
        for edge in response.json()["data"]["edges"]
        if edge["type"] == "links_to"
    }
    assert links == {(proper_id, "target")}


def test_local_graph_uses_table_for_outgoing_and_backlinks(api):
    client, db = api
    center_id = _note(db, "center", "中心").id
    neighbor_id = _note(db, "neighbor", "邻居").id
    _note(db, "legacy-backlink", "仅 JSON 反链", linked=["center"])

    db.add(NoteLink(source_id=center_id, target_id=neighbor_id))
    backlink_id = client.post("/api/notes", json={
        "title": "真实反链来源",
        "content": "引用 [[中心]]",
    }).json()["data"]["id"]

    response = client.get(f"/api/graph/local/{center_id}")

    assert response.status_code == 200
    data = response.json()["data"]
    links = {
        (edge["source"], edge["target"])
        for edge in data["edges"] if edge["type"] == "links_to"
    }
    assert links == {(center_id, neighbor_id), (backlink_id, center_id)}
    assert {node["id"] for node in data["nodes"]} == {center_id, neighbor_id, backlink_id}


def test_migration_is_idempotent_and_matches_existing_links(api):
    """迁移对拍：每个来源的关联表出链集合 == JSON 中存在的目标集合；重复执行不新增。"""
    from migrate_note_links import migrate_note_links

    client, db = api
    _note(db, "t1", "目标1")
    _note(db, "t2", "目标2")
    _note(db, "s1", "来源1", linked=["t1", "t1", "ghost"])
    s2 = _note(db, "s2", "来源2", linked=["t2"])
    db.add(NoteLink(source_id=s2.id, target_id="t2"))
    bad = _note(db, "bad", "坏 JSON")
    bad.linked_note_ids = '{"not": "a list"}'
    db.commit()

    first = migrate_note_links(db)
    db.commit()
    assert first == {"inserted": 1, "skipped_bad_json": 1, "skipped_missing_target": 1}

    second = migrate_note_links(db)
    assert second["inserted"] == 0

    note_ids = {note.id for note in db.query(Note).all()}
    for note in db.query(Note).all():
        try:
            legacy = set(json.loads(note.linked_note_ids or "[]")) & note_ids
        except (TypeError, ValueError):
            legacy = set()
        migrated = {row[0] for row in db.query(NoteLink.target_id).filter_by(source_id=note.id).all()}
        assert migrated == legacy


def test_note_detail_and_list_read_links_from_table(api):
    client, db = api
    _note(db, "target", "目标")
    source_id = client.post("/api/notes", json={
        "title": "来源",
        "content": "引用 [[目标]]",
    }).json()["data"]["id"]
    # 模拟回滚保险字段损坏：接口仍应从关联表给出正确出链
    source = db.query(Note).filter_by(id=source_id).one()
    source.linked_note_ids = "[]"
    db.commit()

    detail = client.get(f"/api/notes/{source_id}").json()["data"]
    assert detail["linked_note_ids"] == ["target"]

    items = client.get("/api/notes").json()["data"]["items"]
    assert next(item for item in items if item["id"] == source_id)["linked_note_ids"] == ["target"]
