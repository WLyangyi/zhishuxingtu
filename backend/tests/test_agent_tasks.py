# -*- coding: utf-8 -*-
"""二期 2.1：agent_tasks 表——task 分层的地基。

覆盖三件 2.1 DoD：
1. 表结构与 core_intent 下沉字段就位（goal/constraints/acceptance_criteria/
   intent_version/intent_versions/depends_on），为 2.2/2.3/2.5 铺路；
2. `WHERE status='active'` 部分唯一索引：同一会话同一时刻仅一个 active 任务，
   completed/cancelled/archived 不受限，active 转非 active 后释放名额；
3. phase（执行阶段）与 status（生命周期）职责分离，互不影响。
另覆盖迁移脚本幂等（建表 + 索引 + 重复执行跳过）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.agent_session import AgentTask


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _task(session, sid="s1", status="active", phase="executing", **kw):
    t = AgentTask(
        session_id=sid, user_id="u1", title="任务", status=status, phase=phase, **kw
    )
    session.add(t)
    return t


# ---------- 1. 表结构与 core_intent 下沉字段 ----------
def test_table_has_core_intent_and_phase_status_columns(db):
    cols = {row[1] for row in db.execute(text("PRAGMA table_info(agent_tasks)")).fetchall()}
    for c in (
        "id", "session_id", "user_id", "title",
        "goal", "constraints", "acceptance_criteria",
        "intent_version", "intent_versions",
        "phase", "status", "depends_on",
        "created_at", "updated_at",
    ):
        assert c in cols, f"缺列: {c}"


def test_core_intent_fields_writable_and_roundtrip(db):
    t = AgentTask(
        session_id="s1",
        user_id="u1",
        goal="写一份周报",
        constraints=json.dumps({"tone": "正式", "language": "中文"}),
        acceptance_criteria=json.dumps(["包含本周结论", "下周计划"]),
        intent_version=1,
    )
    db.add(t)
    db.commit()
    db.refresh(t)

    assert t.goal == "写一份周报"
    assert json.loads(t.constraints) == {"tone": "正式", "language": "中文"}
    assert json.loads(t.acceptance_criteria) == ["包含本周结论", "下周计划"]
    assert t.intent_version == 1


def test_intent_versions_and_depends_on_writable(db):
    hist = json.dumps([{"version": 1, "change_type": "init", "goal": "写周报"}])
    t = AgentTask(
        session_id="s1", user_id="u1", intent_versions=hist, depends_on="task-parent"
    )
    db.add(t)
    db.commit()
    db.refresh(t)

    assert json.loads(t.intent_versions)[0]["change_type"] == "init"
    assert t.depends_on == "task-parent"


# ---------- 2. 部分唯一索引（WHERE status='active'） ----------
def test_only_one_active_task_per_session(db):
    _task(db, sid="s1", status="active")
    db.commit()
    _task(db, sid="s1", status="active")
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_multiple_completed_tasks_allowed(db):
    _task(db, sid="s1", status="completed")
    _task(db, sid="s1", status="completed")
    db.commit()
    assert db.query(AgentTask).filter_by(session_id="s1").count() == 2


def test_active_plus_completed_allowed(db):
    _task(db, sid="s1", status="active")
    _task(db, sid="s1", status="completed")
    db.commit()
    assert db.query(AgentTask).filter_by(session_id="s1").count() == 2


def test_active_plus_cancelled_allowed(db):
    _task(db, sid="s1", status="active")
    _task(db, sid="s1", status="cancelled")
    db.commit()
    assert db.query(AgentTask).filter_by(session_id="s1").count() == 2


def test_different_sessions_each_have_active(db):
    _task(db, sid="s1", status="active")
    _task(db, sid="s2", status="active")
    db.commit()
    assert db.query(AgentTask).filter_by(status="active").count() == 2


def test_active_to_completed_frees_slot_for_new_active(db):
    t1 = _task(db, sid="s1", status="active")
    db.commit()
    t1.status = "completed"
    db.commit()
    # 名额释放后可再建 active
    _task(db, sid="s1", status="active")
    db.commit()
    assert db.query(AgentTask).filter_by(session_id="s1", status="active").count() == 1


def test_active_to_archived_frees_slot(db):
    t1 = _task(db, sid="s1", status="active")
    db.commit()
    t1.status = "archived"
    db.commit()
    _task(db, sid="s1", status="active")
    db.commit()
    assert db.query(AgentTask).filter_by(session_id="s1", status="active").count() == 1


# ---------- 3. phase / status 职责分离 ----------
def test_phase_and_status_independent(db):
    t = AgentTask(session_id="s1", user_id="u1", phase="review", status="active")
    db.add(t)
    db.commit()
    db.refresh(t)
    assert t.phase == "review"
    assert t.status == "active"

    # phase 变化不触碰 status，唯一约束仍只看 status
    t.phase = "done"
    db.commit()
    db.refresh(t)
    assert t.phase == "done"
    assert t.status == "active"


def test_phase_change_does_not_free_active_slot(db):
    t1 = _task(db, sid="s1", status="active", phase="executing")
    db.commit()
    # phase 跑到 done，但任务仍 active，名额不释放
    t1.phase = "done"
    db.commit()
    _task(db, sid="s1", status="active")
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_default_phase_and_status(db):
    t = AgentTask(session_id="s1", user_id="u1")
    db.add(t)
    db.commit()
    db.refresh(t)
    assert t.phase == "clarify"
    assert t.status == "active"


# ---------- 4. 迁移脚本幂等 ----------
def test_migration_creates_table_with_partial_index(db):
    from scripts.migrate_agent_tasks import ensure_agent_tasks_table

    Base.metadata.drop_all(db.get_bind())
    created = ensure_agent_tasks_table(db)
    assert created is True

    cols = {row[1] for row in db.execute(text("PRAGMA table_info(agent_tasks)")).fetchall()}
    assert "phase" in cols and "status" in cols

    idx = db.execute(
        text(
            "SELECT sql FROM sqlite_master WHERE type='index' "
            "AND name='uq_agent_tasks_active_per_session'"
        )
    ).fetchone()
    assert idx is not None
    sql = idx[0].lower()
    assert "unique" in sql and "where" in sql and "status='active'" in sql


def test_migration_is_idempotent(db):
    from scripts.migrate_agent_tasks import ensure_agent_tasks_table

    Base.metadata.drop_all(db.get_bind())
    assert ensure_agent_tasks_table(db) is True
    assert ensure_agent_tasks_table(db) is False  # 第二次跳过


def test_migration_index_blocks_two_active(db):
    from scripts.migrate_agent_tasks import ensure_agent_tasks_table

    Base.metadata.drop_all(db.get_bind())
    ensure_agent_tasks_table(db)

    db.add(AgentTask(session_id="s1", user_id="u1", status="active"))
    db.commit()
    db.add(AgentTask(session_id="s1", user_id="u1", status="active"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
