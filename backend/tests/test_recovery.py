# -*- coding: utf-8 -*-
"""三期3.4:断流恢复核对流程(TDD)。

验证 reconcile_recovery:
- 写工具(create_note)副作用已落地(Note 已落库)→ action=confirmed,行补记 succeeded
- 写工具副作用未确认(无 Note)→ action=unknown
- 读工具无副作用 → action=unknown
- 报告 confirmed/unknown/total/has_pending 统计正确
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.agent_session import AgentToolCall
from app.models.note import Note
from app.services.agent.recovery import reconcile_recovery
from app.services.agent.tool_ops import (
    STATUS_SUCCEEDED,
    compute_operation_id,
    register_planned,
)


@pytest.fixture()
def engine(monkeypatch):
    import app.services.agent.recovery as recovery_mod

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AgentToolCall.__table__.create(engine)
    Note.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(recovery_mod, "SessionLocal", Session)
    yield engine
    engine.dispose()


def _add_planned(engine, session_id, tool_name, args, tool_call_id):
    op = compute_operation_id(session_id, tool_name, args)
    s = sessionmaker(bind=engine)()
    register_planned(session_id, tool_call_id, tool_name, args, op, db=s)
    s.close()
    return op


def test_reconcile_confirmed_when_note_exists(engine):
    """写工具副作用已落地(Note 已落库)→ confirmed,行补记 succeeded。"""
    op = _add_planned(engine, "s1", "create_note", {"title": "T", "content": "C"}, "call_1")
    # 副作用已落地:Note 按 idempotency_key 落库
    s = sessionmaker(bind=engine)()
    s.add(Note(title="T", content="C", user_id="u1", idempotency_key="agent:s1:call_1"))
    s.commit()
    s.close()

    report = reconcile_recovery("s1", "u1")
    assert report["total"] == 1
    assert report["confirmed"] == 1
    assert report["unknown"] == 0
    assert report["has_pending"] is True
    item = report["items"][0]
    assert item["action"] == "confirmed"
    assert item["confirmed"] is True
    # 行被补记为 succeeded
    s = sessionmaker(bind=engine)()
    row = s.query(AgentToolCall).filter_by(tool_call_id="call_1").first()
    s.close()
    assert row.status == STATUS_SUCCEEDED


def test_reconcile_unknown_when_note_absent(engine):
    """写工具副作用未确认(无 Note)→ unknown,行保持 planned。"""
    op = _add_planned(engine, "s1", "create_note", {"title": "T", "content": "C"}, "call_2")
    report = reconcile_recovery("s1", "u1")
    assert report["total"] == 1
    assert report["unknown"] == 1
    assert report["items"][0]["action"] == "unknown"
    assert report["items"][0]["confirmed"] is False
    # 行仍 planned
    s = sessionmaker(bind=engine)()
    row = s.query(AgentToolCall).filter_by(tool_call_id="call_2").first()
    s.close()
    assert row.status == "planned"


def test_reconcile_read_tool_unknown(engine):
    """读工具无副作用 → unknown(仅报告)。"""
    _add_planned(engine, "s1", "search_notes", {"query": "vue"}, "call_3")
    report = reconcile_recovery("s1", "u1")
    assert report["total"] == 1
    assert report["unknown"] == 1
    assert report["items"][0]["action"] == "unknown"


def test_reconcile_no_pending_returns_empty(engine):
    """无 planned 行 → 空报告,has_pending=False。"""
    report = reconcile_recovery("s1", "u1")
    assert report["total"] == 0
    assert report["has_pending"] is False
    assert report["items"] == []


def test_reconcile_mixed_confirmed_and_unknown(engine):
    """混合场景:一个 confirmed、一个 unknown。"""
    _add_planned(engine, "s1", "create_note", {"title": "A", "content": "A"}, "call_a")
    _add_planned(engine, "s1", "create_note", {"title": "B", "content": "B"}, "call_b")
    s = sessionmaker(bind=engine)()
    s.add(Note(title="A", content="A", user_id="u1", idempotency_key="agent:s1:call_a"))
    s.commit()
    s.close()
    report = reconcile_recovery("s1", "u1")
    assert report["total"] == 2
    assert report["confirmed"] == 1
    assert report["unknown"] == 1
