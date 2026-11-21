# -*- coding: utf-8 -*-
"""三期3.5:断流恢复核对接口(TDD)。

覆盖 GET /api/agent/sessions/{id}/recovery:
- in_flight:会话处理中 → status=in_flight,不核对
- blocked:有待审批 interrupt → status=blocked,优先提示审批
- ready:无冲突 → status=ready + 恢复报告
检查顺序与 chat_stream 一致:in-flight → 真实 interrupt → 恢复核对。
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.routes.agent import router as agent_router
import app.api.routes.agent as agent_mod
from app.db.base import Base
from app.db.session import get_db
from app.models.agent_session import AgentSession
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
    db.add(user)
    db.add(AgentSession(id="s1", user_id="u1", title="会话"))
    db.commit()

    app = FastAPI()
    app.include_router(agent_router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    with TestClient(app) as client:
        yield client, db

    db.close()
    engine.dispose()


def _fake_graph(interrupts=None):
    """构造 get_graph 返回对象:interrupts 非空则 _pending_approval_payload 命中审批。"""
    tasks = []
    if interrupts:
        tasks.append(SimpleNamespace(interrupts=[SimpleNamespace(value=interrupts)]))
    graph = SimpleNamespace(
        get_state=lambda cfg: SimpleNamespace(
            tasks=tasks, values={}, config={"configurable": {"thread_id": "s1"}}
        )
    )
    return graph


def test_recovery_in_flight(api):
    client, _ = api
    agent_mod._IN_FLIGHT["s1"] = agent_mod.time.time()
    try:
        resp = client.get("/api/agent/sessions/s1/recovery")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "in_flight"
        assert data["recovery"] is None
    finally:
        agent_mod._IN_FLIGHT.pop("s1", None)


def test_recovery_blocked_when_pending_approval(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(
        agent_mod,
        "get_graph",
        lambda: _fake_graph(
            interrupts={"type": "approval_required", "tool_call_id": "c1", "tool_name": "create_note"}
        ),
    )
    resp = client.get("/api/agent/sessions/s1/recovery")
    data = resp.json()["data"]
    assert data["status"] == "blocked"
    assert data["pending_approval"]["type"] == "approval_required"
    assert data["recovery"] is None


def test_recovery_ready_returns_report(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(agent_mod, "get_graph", lambda: _fake_graph())
    fake_report = {
        "items": [{"operation_id": "op:s1:create_note:x", "action": "unknown"}],
        "confirmed": 0,
        "unknown": 1,
        "total": 1,
        "has_pending": True,
    }
    monkeypatch.setattr(agent_mod, "reconcile_recovery", lambda sid, uid, db=None: fake_report)
    resp = client.get("/api/agent/sessions/s1/recovery")
    data = resp.json()["data"]
    assert data["status"] == "ready"
    assert data["recovery"] == fake_report


def test_recovery_ready_empty_when_no_pending(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(agent_mod, "get_graph", lambda: _fake_graph())
    monkeypatch.setattr(
        agent_mod,
        "reconcile_recovery",
        lambda sid, uid, db=None: {
            "items": [], "confirmed": 0, "unknown": 0, "total": 0, "has_pending": False
        },
    )
    resp = client.get("/api/agent/sessions/s1/recovery")
    data = resp.json()["data"]
    assert data["status"] == "ready"
    assert data["recovery"]["has_pending"] is False
