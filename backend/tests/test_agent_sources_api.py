import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, HumanMessage
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.routes import agent as agent_route
from app.db.base import Base
from app.db.session import get_db
from app.models.agent_session import AgentSession
from app.models.user import User
from app.services.agent.sources import build_web_sources


def _events(chunks):
    return [
        json.loads(chunk.removeprefix("data: ").strip())
        for chunk in chunks
        if chunk.strip() != "data: [DONE]"
    ]


def test_stream_graph_emits_sources_after_final_answer(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    session = AgentSession(id="s1", title="联网问答", user_id="u1")
    db.add(session)
    db.commit()

    sources = build_web_sources(
        [{"title": "页面", "url": "https://example.com/a", "snippet": "摘要"}],
        "s1",
    )
    final_message = AIMessage(
        content="回答 [1]",
        id="a1",
        additional_kwargs={"sources": sources},
    )

    class FakeGraph:
        def stream(self, graph_input, config):
            yield {"output": {"answer": "回答 [1]", "messages": [final_message]}}

        def get_state(self, config):
            return SimpleNamespace(values={
                "current_agent": "web_search",
                "messages": [final_message],
            })

    monkeypatch.setattr(agent_route, "get_graph", lambda: FakeGraph())
    try:
        events = _events(list(agent_route._stream_graph(db, {}, session, "u1")))
    finally:
        db.close()
        engine.dispose()

    assert [event["type"] for event in events] == ["final_answer", "sources", "usage"]
    assert events[1] == {
        "type": "sources",
        "session_id": "s1",
        "message_id": "a1",
        "sources": sources,
    }


def test_stream_graph_emits_visual_evidence_after_final_answer(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    session = AgentSession(id="s1", title="视觉问答", user_id="u1")
    db.add(session)
    db.commit()
    evidence = [{
        "asset_id": "asset-1",
        "note_id": "n1",
        "page_number": 1,
        "source_filename": "visual.pdf",
        "description": "图表描述",
        "description_status": "completed",
        "image_url": "/api/import/notes/n1/assets/asset-1/image",
    }]
    final_message = AIMessage(
        content="已对照原图回答",
        id="a1",
        additional_kwargs={"visual_evidence": evidence},
    )

    class FakeGraph:
        def stream(self, graph_input, config):
            yield {"output": {"answer": "已对照原图回答", "messages": [final_message]}}

        def get_state(self, config):
            return SimpleNamespace(values={"current_agent": "knowledge", "messages": [final_message]})

    monkeypatch.setattr(agent_route, "get_graph", lambda: FakeGraph())
    try:
        events = _events(list(agent_route._stream_graph(db, {}, session, "u1")))
    finally:
        db.close()
        engine.dispose()

    assert [event["type"] for event in events] == ["final_answer", "visual_evidence", "usage"]
    assert events[1]["visual_evidence"] == evidence
    assert events[1]["message_id"] == "a1"


def test_session_messages_restore_message_id_and_sources(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id="u1", username="tester", password_hash="x")
    db.add_all([
        user,
        AgentSession(id="s1", title="联网问答", user_id="u1"),
    ])
    db.commit()
    sources = build_web_sources(
        [{"title": "页面", "url": "https://example.com/a", "snippet": "摘要"}],
        "s1",
    )

    class FakeGraph:
        def get_state(self, config):
            return SimpleNamespace(values={"messages": [
                HumanMessage(content="问题", id="h1"),
                AIMessage(content="回答 [1]", id="a1", additional_kwargs={"sources": sources}),
            ]})

    monkeypatch.setattr(agent_route, "get_graph", lambda: FakeGraph())
    app = FastAPI()
    app.include_router(agent_route.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            response = client.get("/api/agent/sessions/s1/messages")
    finally:
        db.close()
        engine.dispose()

    assert response.status_code == 200
    assistant = response.json()["data"]["messages"][1]
    assert assistant["id"] == "a1"
    assert assistant["sources"] == sources


def test_session_messages_restore_visual_evidence(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id="u1", username="tester", password_hash="x")
    db.add_all([user, AgentSession(id="s1", title="视觉问答", user_id="u1")])
    db.commit()
    evidence = [{
        "asset_id": "asset-1",
        "note_id": "n1",
        "page_number": 1,
        "source_filename": "visual.pdf",
        "description": "图表描述",
        "description_status": "completed",
        "image_url": "/api/import/notes/n1/assets/asset-1/image",
    }]

    class FakeGraph:
        def get_state(self, config):
            return SimpleNamespace(values={"messages": [
                HumanMessage(content="问题", id="h1"),
                AIMessage(content="答案", id="a1", additional_kwargs={"visual_evidence": evidence}),
            ]})

    monkeypatch.setattr(agent_route, "get_graph", lambda: FakeGraph())
    app = FastAPI()
    app.include_router(agent_route.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            response = client.get("/api/agent/sessions/s1/messages")
    finally:
        db.close()
        engine.dispose()

    assert response.status_code == 200
    assistant = response.json()["data"]["messages"][1]
    assert assistant["visual_evidence"] == evidence


def test_session_messages_filter_malformed_sources_without_renumbering(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id="u1", username="tester", password_hash="x")
    db.add_all([
        user,
        AgentSession(id="s1", title="联网问答", user_id="u1"),
    ])
    db.commit()
    sources = build_web_sources(
        [
            {"title": "第一页", "url": "https://example.com/a", "snippet": "摘要一"},
            {"title": "第二页", "url": "https://example.com/b", "snippet": "摘要二"},
        ],
        "s1",
    )
    malformed = {"ordinal": 99, "title": "缺少稳定标识"}

    class FakeGraph:
        def get_state(self, config):
            return SimpleNamespace(values={"messages": [
                AIMessage(
                    content="回答 [1] [2]",
                    id="a1",
                    additional_kwargs={"sources": [sources[0], malformed, sources[1]]},
                ),
            ]})

    monkeypatch.setattr(agent_route, "get_graph", lambda: FakeGraph())
    app = FastAPI()
    app.include_router(agent_route.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            response = client.get("/api/agent/sessions/s1/messages")
    finally:
        db.close()
        engine.dispose()

    assert response.status_code == 200
    assistant = response.json()["data"]["messages"][0]
    assert assistant["sources"] == sources
    assert [source["ordinal"] for source in assistant["sources"]] == [1, 2]


def test_stream_graph_omits_sources_for_local_answer(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    session = AgentSession(id="s-local", title="本地问答", user_id="u1")
    db.add(session)
    db.commit()
    final_message = AIMessage(content="本地回答", id="a-local")

    class FakeGraph:
        def stream(self, graph_input, config):
            yield {"output": {"answer": "本地回答", "messages": [final_message]}}

        def get_state(self, config):
            return SimpleNamespace(values={
                "current_agent": "knowledge",
                "messages": [final_message],
            })

    monkeypatch.setattr(agent_route, "get_graph", lambda: FakeGraph())
    try:
        events = _events(list(agent_route._stream_graph(db, {}, session, "u1")))
    finally:
        db.close()
        engine.dispose()

    assert [event["type"] for event in events] == ["final_answer", "usage"]
    assert events[0]["answer"] == "本地回答"


def test_stream_graph_filters_malformed_sources(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    session = AgentSession(id="s1", title="联网问答", user_id="u1")
    db.add(session)
    db.commit()
    sources = build_web_sources(
        [{"title": "页面", "url": "https://example.com/a", "snippet": "摘要"}],
        "s1",
    )
    final_message = AIMessage(
        content="回答 [1]",
        id="a1",
        additional_kwargs={"sources": [{"ordinal": 1}, sources[0]]},
    )

    class FakeGraph:
        def stream(self, graph_input, config):
            yield {"output": {"answer": "回答 [1]", "messages": [final_message]}}

        def get_state(self, config):
            return SimpleNamespace(values={
                "current_agent": "web_search",
                "messages": [final_message],
            })

    monkeypatch.setattr(agent_route, "get_graph", lambda: FakeGraph())
    try:
        events = _events(list(agent_route._stream_graph(db, {}, session, "u1")))
    finally:
        db.close()
        engine.dispose()

    assert [event["type"] for event in events] == ["final_answer", "sources", "usage"]
    assert events[1]["sources"] == sources


def test_session_messages_keep_legacy_assistant_message_compatible(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id="u1", username="tester", password_hash="x")
    db.add_all([
        user,
        AgentSession(id="s1", title="历史会话", user_id="u1"),
    ])
    db.commit()

    class FakeGraph:
        def get_state(self, config):
            return SimpleNamespace(values={"messages": [
                AIMessage(content="旧回答"),
            ]})

    monkeypatch.setattr(agent_route, "get_graph", lambda: FakeGraph())
    app = FastAPI()
    app.include_router(agent_route.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            response = client.get("/api/agent/sessions/s1/messages")
    finally:
        db.close()
        engine.dispose()

    assert response.status_code == 200
    assert response.json()["data"]["messages"] == [{
        "role": "assistant",
        "id": "",
        "content": "旧回答",
        "sources": [],
    }]


def test_session_messages_reject_other_users_session(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id="u1", username="tester", password_hash="x")
    other = User(id="u2", username="other", password_hash="x")
    db.add_all([
        user,
        other,
        AgentSession(id="s-other", title="别人的会话", user_id="u2"),
    ])
    db.commit()

    def unexpected_graph_access():
        raise AssertionError("跨用户会话不应读取 checkpoint")

    monkeypatch.setattr(agent_route, "get_graph", unexpected_graph_access)
    app = FastAPI()
    app.include_router(agent_route.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            response = client.get("/api/agent/sessions/s-other/messages")
    finally:
        db.close()
        engine.dispose()

    assert response.status_code == 404
    assert response.json()["detail"] == "会话不存在"


def test_stream_graph_does_not_emit_sources_after_interrupt(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    session = AgentSession(id="s1", title="联网问答", user_id="u1")
    db.add(session)
    db.commit()
    sources = build_web_sources(
        [{"title": "页面", "url": "https://example.com/a", "snippet": "摘要"}],
        "s1",
    )
    final_message = AIMessage(
        content="回答 [1]",
        id="a1",
        additional_kwargs={"sources": sources},
    )

    class FakeGraph:
        def stream(self, graph_input, config):
            yield {"output": {"answer": "回答 [1]", "messages": [final_message]}}
            yield {"__interrupt__": [SimpleNamespace(value={
                "type": "approval_required",
                "tool_call_id": "call-1",
                "tool_name": "create_note",
                "args": {},
            })]}

        def get_state(self, config):
            return SimpleNamespace(values={
                "current_agent": "web_search",
                "messages": [final_message],
            })

    monkeypatch.setattr(agent_route, "get_graph", lambda: FakeGraph())
    try:
        events = _events(list(agent_route._stream_graph(db, {}, session, "u1")))
    finally:
        db.close()
        engine.dispose()

    assert [event["type"] for event in events] == ["approval_required", "usage"]


def test_budget_hard_stop_never_emits_sources():
    session = AgentSession(id="s1", title="联网问答", user_id="u1")

    events = _events(agent_route._budget_exceeded_stream(session, "达上限"))

    assert [event["type"] for event in events] == ["budget_exceeded", "final_answer"]
