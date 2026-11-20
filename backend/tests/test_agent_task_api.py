# -*- coding: utf-8 -*-
"""二期 2.6:task 创建/切换/恢复接口。

覆盖:
- POST /api/agent/sessions/{id}/tasks 创建任务(建 active、旧 active 完成);
- GET /api/agent/sessions/{id}/tasks 列表(标注当前 active);
- POST .../tasks/{tid}/switch 切换当前任务;
- POST .../tasks/{tid}/restore 恢复非 active 任务。
"""
import json
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
from app.models.agent_session import AgentSession, AgentTask
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
    db.add(AgentTask(id="t1", session_id="s1", user_id="u1", status="active", title="任务一", goal="写周报"))
    db.add(AgentTask(id="t2", session_id="s1", user_id="u1", status="completed", title="任务二"))
    db.commit()

    app = FastAPI()
    app.include_router(agent_router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    with TestClient(app) as client:
        yield client, db

    db.close()
    engine.dispose()


def test_create_task_sets_active_and_completes_old(api):
    client, db = api
    resp = client.post(
        "/api/agent/sessions/s1/tasks",
        json={"title": "任务三", "goal": "做调研"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "任务三"
    assert data["status"] == "active"

    db.expire_all()
    old = db.query(AgentTask).filter_by(id="t1").first()
    assert old.status == "completed"  # 旧 active 完成
    new = db.query(AgentTask).filter_by(id=data["id"]).first()
    assert new.status == "active"
    assert new.goal == "做调研"


def test_list_tasks_marks_current_active(api):
    client, _ = api
    resp = client.get("/api/agent/sessions/s1/tasks")
    assert resp.status_code == 200
    tasks = resp.json()["data"]
    assert len(tasks) == 2
    active = [t for t in tasks if t["status"] == "active"]
    assert len(active) == 1
    assert active[0]["is_current"] is True
    completed = [t for t in tasks if t["status"] == "completed"]
    assert all(t["is_current"] is False for t in completed)


def test_switch_task_completes_old_and_activates_target(api):
    client, db = api
    resp = client.post("/api/agent/sessions/s1/tasks/t2/switch")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == "t2"
    assert data["status"] == "active"

    db.expire_all()
    assert db.query(AgentTask).filter_by(id="t1").first().status == "completed"
    assert db.query(AgentTask).filter_by(id="t2").first().status == "active"


def test_switch_nonexistent_task_404(api):
    client, _ = api
    resp = client.post("/api/agent/sessions/s1/tasks/nope/switch")
    assert resp.status_code == 404


def test_switch_other_users_task_forbidden(api):
    client, db = api
    db.add(AgentTask(id="t_other", session_id="s_other", user_id="u2", status="active"))
    db.commit()
    resp = client.post("/api/agent/sessions/s1/tasks/t_other/switch")
    assert resp.status_code == 404  # 不属于本会话,不暴露


def test_restore_completed_task(api):
    client, db = api
    # t2 是 completed,恢复它
    resp = client.post("/api/agent/sessions/s1/tasks/t2/restore")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == "t2"
    assert data["status"] == "active"

    db.expire_all()
    assert db.query(AgentTask).filter_by(id="t2").first().status == "active"
    # 原 active(t1)被完成
    assert db.query(AgentTask).filter_by(id="t1").first().status == "completed"


def test_restore_already_active_is_noop(api):
    client, db = api
    # t1 已是 active,恢复它不应报错,状态不变
    resp = client.post("/api/agent/sessions/s1/tasks/t1/restore")
    assert resp.status_code == 200
    db.expire_all()
    assert db.query(AgentTask).filter_by(id="t1").first().status == "active"


def test_list_tasks_scoped_to_session(api):
    client, db = api
    db.add(AgentTask(id="t_other", session_id="s_other", user_id="u1", status="active"))
    db.commit()
    resp = client.get("/api/agent/sessions/s1/tasks")
    tasks = resp.json()["data"]
    ids = {t["id"] for t in tasks}
    assert "t_other" not in ids  # 不跨会话
