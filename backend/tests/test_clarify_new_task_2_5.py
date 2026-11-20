# -*- coding: utf-8 -*-
"""二期 2.5:clarify / new_task 闭环。

用户输入驱动的四分类编排(pending_clarification 激活时):
- confirm: 确认当前方案 → 清除待澄清,继续当前任务;
- revise:  修改需求 → 更新 core_intent(revise),清除待澄清;
- new_task:换任务 → 建新 task、切 current_task_id、旧 task 完成(depends_on 失效);
- continue:直接回答澄清问题 → 清除待澄清,继续。

无 pending_clarification 时 handle_clarification 为空操作。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.agent_session import AgentSession, AgentTask
from app.services.agent.nodes import (
    classify_clarification_response,
    handle_clarification,
)


@pytest.fixture()
def db_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    session = factory()
    session.add(AgentSession(id="s1", user_id="u1"))
    session.add(AgentTask(id="t_old", session_id="s1", user_id="u1", status="active", goal="旧任务"))
    session.commit()
    yield factory
    session.close()
    engine.dispose()


# ---------- 四分类裁决 ----------
@pytest.mark.parametrize("q", ["确认", "对", "是的", "好的", "可以", "没问题"])
def test_classify_confirm(q):
    assert classify_clarification_response(q) == "confirm"


@pytest.mark.parametrize("q", ["改成列表", "修改一下目标", "不对,应该是", "调整为表格"])
def test_classify_revise(q):
    assert classify_clarification_response(q) == "revise"


@pytest.mark.parametrize("q", ["换个任务", "新任务:做周报", "换一个", "另一个任务"])
def test_classify_new_task(q):
    assert classify_clarification_response(q) == "new_task"


@pytest.mark.parametrize("q", ["面向管理层", "字数控制在500字", "用正式语气"])
def test_classify_continue(q):
    assert classify_clarification_response(q) == "continue"


# ---------- 无待澄清时空操作 ----------
def test_handle_clarification_noop_without_pending():
    state = {"session_id": "s1", "messages": []}
    assert handle_clarification(state) == {}


# ---------- confirm:清除待澄清 ----------
def test_handle_confirm_clears_pending():
    state = {
        "session_id": "s1",
        "pending_clarification": {"question": "目标受众是?"},
        "messages": [],
    }
    out = handle_clarification(state)
    assert out["pending_clarification"] is None


# ---------- continue:清除待澄清 ----------
def test_handle_continue_clears_pending():
    state = {
        "session_id": "s1",
        "pending_clarification": {"question": "目标受众是?"},
        "messages": [],
    }
    out = handle_clarification(state, question="面向管理层")
    assert out["pending_clarification"] is None


# ---------- revise:更新锚点 + 清除待澄清 ----------
def test_handle_revise_updates_anchor_and_clears():
    state = {
        "session_id": "s1",
        "current_task_id": "t_old",
        "core_intent": {"goal": "写周报", "constraints": {}, "acceptance_criteria": []},
        "intent_version": 1,
        "pending_clarification": {"question": "要什么格式?"},
        "messages": [],
    }
    out = handle_clarification(state, question="改成列表格式")
    assert out["pending_clarification"] is None
    assert out["core_intent"]["constraints"].get("format") == "列表"
    assert out["intent_version"] == 2


# ---------- new_task:建任务 + 切换 + 旧任务完成 ----------
def test_handle_new_task_creates_and_switches(db_factory, monkeypatch):
    monkeypatch.setattr("app.db.session.SessionLocal", db_factory)
    state = {
        "session_id": "s1",
        "user_id": "u1",
        "current_task_id": "t_old",
        "pending_clarification": {"question": "要继续这个还是换任务?"},
        "messages": [],
    }
    out = handle_clarification(state, question="换个任务")

    assert out["pending_clarification"] is None
    assert out["current_task_id"] != "t_old"
    assert out["phase"] == "clarify"
    assert out["status"] == "active"
    # 新任务建立且 depends_on 指向旧任务
    db = db_factory()
    try:
        new_task = db.query(AgentTask).filter_by(id=out["current_task_id"]).first()
        assert new_task is not None
        assert new_task.status == "active"
        assert new_task.depends_on == "t_old"
        # 旧任务完成,释放 active 名额(部分唯一索引生效)
        old = db.query(AgentTask).filter_by(id="t_old").first()
        assert old.status == "completed"
    finally:
        db.close()


def test_handle_new_task_frees_active_slot(db_factory, monkeypatch):
    """切 task 后同会话仅一个新 active(旧 active 转 completed,唯一约束不冲突)。"""
    monkeypatch.setattr("app.db.session.SessionLocal", db_factory)
    state = {
        "session_id": "s1",
        "user_id": "u1",
        "current_task_id": "t_old",
        "pending_clarification": {"question": "换任务?"},
        "messages": [],
    }
    out = handle_clarification(state, question="新任务:做周报")
    db = db_factory()
    try:
        actives = db.query(AgentTask).filter_by(session_id="s1", status="active").all()
        assert len(actives) == 1
        assert actives[0].id == out["current_task_id"]
    finally:
        db.close()


# ---------- intent_classify 集成:澄清编排在节点内端到端生效 ----------
def test_intent_classify_confirm_clears_pending(monkeypatch):
    from app.services.agent import nodes

    monkeypatch.setattr(nodes, "CORE_INTENT_ENABLED", "on")
    monkeypatch.setattr(nodes.settings, "FORCE_INTENT", "knowledge")
    state = {
        "session_id": "s1",
        "user_id": "u1",
        "question": "确认",
        "pending_clarification": {"question": "目标受众?"},
        "messages": [],
        "core_intent": {"goal": "写周报", "constraints": {}, "acceptance_criteria": []},
        "intent_version": 1,
    }
    out = nodes.intent_classify(state)
    assert out["pending_clarification"] is None
    assert out["intent"] == "knowledge"


def test_intent_classify_new_task_switches(monkeypatch, db_factory):
    monkeypatch.setattr("app.db.session.SessionLocal", db_factory)
    from app.services.agent import nodes

    monkeypatch.setattr(nodes, "CORE_INTENT_ENABLED", "on")
    monkeypatch.setattr(nodes.settings, "FORCE_INTENT", "knowledge")
    state = {
        "session_id": "s1",
        "user_id": "u1",
        "question": "换个任务",
        "current_task_id": "t_old",
        "pending_clarification": {"question": "换任务?"},
        "messages": [],
        "core_intent": {"goal": "旧", "constraints": {}, "acceptance_criteria": []},
        "intent_version": 1,
    }
    out = nodes.intent_classify(state)
    assert out["pending_clarification"] is None
    assert out["current_task_id"] != "t_old"
    assert out["core_intent"] == {}  # 新任务清旧锚点
