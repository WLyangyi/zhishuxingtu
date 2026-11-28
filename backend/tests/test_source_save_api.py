import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.routes import agent as agent_route
from app.db.base import Base
from app.db.session import get_db
from app.models import AgentSession, Note, User
from app.models.agent_session import AgentToolArtifact
from app.models.note_link import NoteLink
from app.services.agent.sources import build_web_sources
from app.services.tools import web_tools


@pytest.fixture()
def api(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    db = factory()
    user = User(id="u1", username="tester", password_hash="x")
    db.add_all([
        user,
        AgentSession(id="s1", title="联网问答", user_id="u1"),
    ])
    db.commit()

    import app.db.session as db_session
    import app.services.bm25_service as bm25_mod
    import app.services.vector_store_adapter as vector_mod

    class DummyBM25:
        is_ready = False

    monkeypatch.setattr(db_session, "SessionLocal", factory)
    monkeypatch.setattr(vector_mod, "get_vector_store_adapter", lambda: None)
    monkeypatch.setattr(bm25_mod, "get_bm25_service", lambda: DummyBM25())

    app = FastAPI()
    app.include_router(agent_route.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            yield SimpleNamespace(client=client, db=db, factory=factory, monkeypatch=monkeypatch, app=app)
    finally:
        db.close()
        engine.dispose()


def _source(api, *, body="完整正文", artifact_id="artifact-1", truncated=False, fetch_failed=False):
    doc = {
        "title": "页面标题",
        "url": "https://example.com/a",
        "full_content": body,
        "snippet": "搜索摘要",
        "fetch_failed": fetch_failed,
        "artifact_id": artifact_id,
        "fetched_at": "2026-11-28T10:00:00+00:00",
        "retrieved_at": "2026-11-28T09:59:00+00:00",
        "truncated": truncated,
    }
    source = build_web_sources([doc], session_id="s1")[0]
    if artifact_id:
        api.db.add(AgentToolArtifact(
            id=artifact_id,
            session_id="s1",
            tool_call_id="fetch-1",
            tool_name="web_fetch",
            content=json.dumps({
                "title": doc["title"],
                "url": doc["url"],
                "content": body,
                "fetched_at": doc["fetched_at"],
                "truncated": truncated,
            }, ensure_ascii=False),
            length=len(body),
        ))
        api.db.commit()

    class FakeGraph:
        def get_state(self, config):
            messages = []
            if config["configurable"]["thread_id"] == "s1":
                messages = [AIMessage(
                    content="回答 [1]",
                    id="a1",
                    additional_kwargs={"sources": [source]},
                )]
            return SimpleNamespace(values={"messages": messages})

    api.monkeypatch.setattr(agent_route, "get_graph", lambda: FakeGraph())
    return source


def test_save_fetched_source_creates_note(api, monkeypatch):
    source = _source(api)
    fetch_calls = []

    def unexpected_fetch(*args, **kwargs):
        fetch_calls.append((args, kwargs))
        raise AssertionError("保存来源不应重新抓取网页")

    monkeypatch.setattr(web_tools.httpx, "post", unexpected_fetch)

    response = api.client.post(
        f"/api/agent/sessions/s1/sources/{source['source_id']}/save"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "页面标题"
    note = api.db.query(Note).filter_by(id=data["id"]).one()
    assert note.user_id == "u1"
    assert "完整正文" in note.content
    assert fetch_calls == []


def test_saved_source_note_includes_provenance(api):
    source = _source(api)

    response = api.client.post(
        f"/api/agent/sessions/s1/sources/{source['source_id']}/save"
    )

    assert response.status_code == 200
    note = api.db.query(Note).filter_by(id=response.json()["data"]["id"]).one()
    assert source["url"] in note.content
    assert source["retrieved_at"] in note.content
    assert source["fetched_at"] in note.content
    assert "完整正文" in note.content


def test_saved_source_uses_existing_backlink_write_path(api):
    api.db.add(Note(id="target-1", title="目标笔记", content="", user_id="u1"))
    api.db.commit()
    source = _source(api, body="完整正文 [[目标笔记]]")

    response = api.client.post(
        f"/api/agent/sessions/s1/sources/{source['source_id']}/save"
    )

    assert response.status_code == 200
    note_id = response.json()["data"]["id"]
    note = api.db.query(Note).filter_by(id=note_id).one()
    assert "target-1" in json.loads(note.linked_note_ids)
    assert api.db.query(NoteLink).filter_by(source_id=note_id, target_id="target-1").count() == 1


def test_saved_truncated_source_marks_incomplete_body(api):
    source = _source(api, truncated=True)

    response = api.client.post(
        f"/api/agent/sessions/s1/sources/{source['source_id']}/save"
    )

    assert response.status_code == 200
    note = api.db.query(Note).filter_by(id=response.json()["data"]["id"]).one()
    assert "正文已截断" in note.content


def test_repeated_source_save_returns_same_note(api):
    source = _source(api)
    path = f"/api/agent/sessions/s1/sources/{source['source_id']}/save"

    first = api.client.post(path)
    second = api.client.post(path)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    assert api.db.query(Note).count() == 1


def test_summary_source_can_be_saved_without_artifact(api):
    source = _source(api, body="", artifact_id=None)

    response = api.client.post(
        f"/api/agent/sessions/s1/sources/{source['source_id']}/save"
    )

    assert response.status_code == 200
    note = api.db.query(Note).filter_by(id=response.json()["data"]["id"]).one()
    assert "仅搜索摘要" in note.content
    assert "搜索摘要" in note.content


def test_failed_fetch_source_can_be_saved_with_failure_notice(api):
    source = _source(api, body="", artifact_id=None, fetch_failed=True)

    response = api.client.post(
        f"/api/agent/sessions/s1/sources/{source['source_id']}/save"
    )

    assert response.status_code == 200
    note = api.db.query(Note).filter_by(id=response.json()["data"]["id"]).one()
    assert "正文抓取失败" in note.content
    assert "搜索摘要" in note.content


def test_source_save_rejects_artifact_from_another_session(api):
    source = _source(api, artifact_id=None)
    source["artifact_id"] = "artifact-2"
    api.db.add(AgentSession(id="s2", title="其他会话", user_id="u1"))
    api.db.add(AgentToolArtifact(
        id="artifact-2",
        session_id="s2",
        tool_call_id="fetch-2",
        tool_name="web_fetch",
        content=json.dumps({"content": "其他会话正文"}),
        length=6,
    ))
    api.db.commit()

    response = api.client.post(
        f"/api/agent/sessions/s1/sources/{source['source_id']}/save"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "正文快照不可用"
    assert api.db.query(Note).count() == 0


def test_fetched_source_without_snapshot_is_not_saved_as_partial_body(api):
    source = _source(api, artifact_id=None)

    response = api.client.post(
        f"/api/agent/sessions/s1/sources/{source['source_id']}/save"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "正文快照不可用"
    assert api.db.query(Note).count() == 0


def test_unknown_source_returns_not_found_without_creating_note(api):
    _source(api)

    response = api.client.post("/api/agent/sessions/s1/sources/unknown/save")

    assert response.status_code == 404
    assert response.json()["detail"] == "来源不存在"
    assert api.db.query(Note).count() == 0


def test_source_from_one_session_cannot_be_saved_to_another(api):
    source = _source(api)
    api.db.add(AgentSession(id="s2", title="目标会话", user_id="u1"))
    api.db.commit()

    response = api.client.post(
        f"/api/agent/sessions/s2/sources/{source['source_id']}/save"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "来源不存在"
    assert api.db.query(Note).count() == 0


def test_source_cannot_be_saved_by_another_user(api):
    source = _source(api)
    other_user = User(id="u2", username="other", password_hash="x")
    api.db.add(other_user)
    api.db.commit()
    api.app.dependency_overrides[get_current_user] = lambda: other_user

    def unexpected_graph():
        raise AssertionError("归属校验失败时不应读取会话 checkpoint")

    api.monkeypatch.setattr(agent_route, "get_graph", unexpected_graph)

    response = api.client.post(
        f"/api/agent/sessions/s1/sources/{source['source_id']}/save"
    )

    assert response.status_code == 404
    assert api.db.query(Note).count() == 0
