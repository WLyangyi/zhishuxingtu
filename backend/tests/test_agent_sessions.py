# -*- coding: utf-8 -*-
"""P2-6:GET /api/agent/sessions 的 q 关键词过滤 / limit 参数回归。"""
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
from app.api.routes.agent import router as agent_router
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
    other = User(id="u2", username="other", password_hash="x")
    db.add_all([user, other])
    db.commit()

    for sid, title, uid in [
        ("s1", "周报生成讨论", "u1"),
        ("s2", "RAG 检索调优", "u1"),
        ("s3", "另一个周报", "u1"),
        ("s4", "别人的周报", "u2"),
    ]:
        db.add(AgentSession(id=sid, title=title, user_id=uid))
    db.commit()

    app = FastAPI()
    app.include_router(agent_router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    with TestClient(app) as client:
        yield client, db

    db.close()
    engine.dispose()


def test_list_sessions_without_q_returns_all_own(api):
    client, _ = api
    resp = client.get("/api/agent/sessions")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["data"]]
    assert set(ids) == {"s1", "s2", "s3"}


def test_list_sessions_filters_by_title_keyword(api):
    client, _ = api
    resp = client.get("/api/agent/sessions", params={"q": "周报"})
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["data"]]
    assert set(ids) == {"s1", "s3"}


def test_list_sessions_keyword_is_case_insensitive_and_stripped(api):
    client, _ = api
    resp = client.get("/api/agent/sessions", params={"q": "  rag  "})
    ids = [item["id"] for item in resp.json()["data"]]
    assert ids == ["s2"]


def test_list_sessions_empty_keyword_returns_all(api):
    client, _ = api
    resp = client.get("/api/agent/sessions", params={"q": ""})
    ids = [item["id"] for item in resp.json()["data"]]
    assert set(ids) == {"s1", "s2", "s3"}


def test_list_sessions_respects_limit(api):
    client, _ = api
    resp = client.get("/api/agent/sessions", params={"limit": 1})
    ids = [item["id"] for item in resp.json()["data"]]
    assert len(ids) == 1
