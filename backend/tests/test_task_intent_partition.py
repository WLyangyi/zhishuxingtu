# -*- coding: utf-8 -*-
"""二期 2.3:intent_versions 按 task 分区——新 task 历史落 task 表,session 作 legacy 不动。

落库规则:
- 有 current_task_id → core_intent/intent_version/intent_versions 写 task 表;
- 无 current_task_id(legacy)→ 写 session(一期行为不变)。
查询规则:
- 会话当前有 active task → 从 task 表读 core_intent;
- 无 active task 或 task 无锚点 → 从 session 读(legacy)。
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.agent_session import AgentSession, AgentTask
from app.api.routes.agent import (
    _core_intent_full,
    _core_intent_summary,
    _persist_core_intent,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    session.add(AgentSession(id="s1", user_id="u1"))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def _ci(goal="写周报", constraints=None, acceptance=None):
    return {
        "goal": goal,
        "constraints": constraints or {},
        "acceptance_criteria": acceptance or [],
    }


def _change(ct="init", source="llm"):
    return {"change_type": ct, "source": source, "ts": "2026-01-01T00:00:00+00:00"}


# ---------- 落库分区 ----------
def test_persist_writes_task_when_current_task(db):
    task = AgentTask(id="t1", session_id="s1", user_id="u1", status="active")
    db.add(task)
    db.commit()
    session = db.query(AgentSession).filter_by(id="s1").first()
    values = {
        "core_intent": _ci(goal="写周报", constraints={"tone": "正式"}),
        "intent_version": 1,
        "last_intent_change": _change("init"),
        "current_task_id": "t1",
    }
    _persist_core_intent(db, session, values)
    db.commit()
    db.refresh(task)

    assert task.goal == "写周报"
    assert json.loads(task.constraints) == {"tone": "正式"}
    assert json.loads(task.acceptance_criteria) == []
    assert task.intent_version == 1
    versions = json.loads(task.intent_versions)
    assert len(versions) == 1
    assert versions[0]["version"] == 1
    assert versions[0]["change_type"] == "init"
    # session 镜像不动(legacy 不迁移)
    session = db.query(AgentSession).filter_by(id="s1").first()
    assert session.core_intent is None


def test_persist_writes_session_legacy_without_task(db):
    session = db.query(AgentSession).filter_by(id="s1").first()
    values = {
        "core_intent": _ci(goal="老目标"),
        "intent_version": 1,
        "last_intent_change": _change("init"),
    }
    _persist_core_intent(db, session, values)
    db.commit()
    db.refresh(session)

    assert json.loads(session.core_intent)["goal"] == "老目标"
    assert session.intent_version == 1
    versions = json.loads(session.intent_versions)
    assert versions[-1]["version"] == 1


def test_persist_task_history_dedup(db):
    """task 末条 version==当前,再写同版本跳过(不重复追加)。"""
    task = AgentTask(
        id="t1", session_id="s1", user_id="u1", status="active",
        intent_version=1,
        intent_versions=json.dumps([{"version": 1, "change_type": "init"}]),
        goal="写周报",
    )
    db.add(task)
    db.commit()
    session = db.query(AgentSession).filter_by(id="s1").first()
    values = {
        "core_intent": _ci(goal="写周报"),
        "intent_version": 1,
        "last_intent_change": _change("init"),
        "current_task_id": "t1",
    }
    _persist_core_intent(db, session, values)
    db.refresh(task)
    versions = json.loads(task.intent_versions)
    assert len(versions) == 1  # 未追加


def test_persist_task_version_compare_skips_stale(db):
    """checkpoint 版本 < task 版本,不覆盖(防旧值覆盖新值)。"""
    task = AgentTask(
        id="t1", session_id="s1", user_id="u1", status="active",
        intent_version=2, goal="新版本目标",
    )
    db.add(task)
    db.commit()
    session = db.query(AgentSession).filter_by(id="s1").first()
    values = {
        "core_intent": _ci(goal="旧版本目标"),
        "intent_version": 1,
        "last_intent_change": _change("init"),
        "current_task_id": "t1",
    }
    _persist_core_intent(db, session, values)
    db.refresh(task)
    assert task.goal == "新版本目标"  # 未被旧值覆盖


# ---------- 查询分区 ----------
def test_core_intent_full_from_task(db):
    task = AgentTask(
        id="t1", session_id="s1", user_id="u1", status="active",
        goal="写周报",
        constraints=json.dumps({"tone": "正式"}),
        acceptance_criteria=json.dumps(["包含结论"]),
        intent_version=1,
    )
    db.add(task)
    db.commit()
    session = db.query(AgentSession).filter_by(id="s1").first()
    out = _core_intent_full(db, session)
    assert out["goal"] == "写周报"
    assert out["constraints"] == {"tone": "正式"}
    assert out["acceptance_criteria"] == ["包含结论"]


def test_core_intent_full_from_session_legacy(db):
    session = db.query(AgentSession).filter_by(id="s1").first()
    session.core_intent = json.dumps(_ci(goal="老目标"))
    session.intent_version = 1
    db.commit()
    out = _core_intent_full(db, session)
    assert out["goal"] == "老目标"


def test_core_intent_full_none_when_no_anchor(db):
    session = db.query(AgentSession).filter_by(id="s1").first()
    out = _core_intent_full(db, session)
    assert out is None


def test_core_intent_summary_from_task(db):
    task = AgentTask(
        id="t1", session_id="s1", user_id="u1", status="active",
        goal="写一份详尽的周报", intent_version=2,
    )
    db.add(task)
    db.commit()
    session = db.query(AgentSession).filter_by(id="s1").first()
    out = _core_intent_summary(db, session)
    assert out["version"] == 2
    assert out["goal"] == "写一份详尽的周报"


def test_core_intent_summary_from_session_legacy(db):
    session = db.query(AgentSession).filter_by(id="s1").first()
    session.core_intent = json.dumps(_ci(goal="老目标"))
    session.intent_version = 1
    db.commit()
    out = _core_intent_summary(db, session)
    assert out["goal"] == "老目标"
    assert out["version"] == 1
