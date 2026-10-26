# -*- coding: utf-8 -*-
"""Phase 4:工具审计幂等——(session_id, tool_call_id) 唯一索引必须真的拦得住重复写入。

为什么单独测库约束:上层 `_record_id` 用 uuid5 生成确定性主键也能防重,但它只是"约定"。
一旦主键生成方式变化或并发重放,重复审计就会静默写进去;库级唯一索引才是真约束。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models.agent_session import AgentToolCall


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    AgentToolCall.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _row(record_id: str, session_id: str, tool_call_id):
    return AgentToolCall(
        id=record_id,
        session_id=session_id,
        tool_call_id=tool_call_id,
        tool_name="search_notes",
        status="success",
    )


def test_duplicate_tool_call_id_is_rejected(db):
    db.add(_row("rec-1", "s1", "call_abc"))
    db.commit()

    db.add(_row("rec-2", "s1", "call_abc"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_same_tool_call_id_allowed_in_different_sessions(db):
    db.add(_row("rec-1", "s1", "call_abc"))
    db.add(_row("rec-2", "s2", "call_abc"))
    db.commit()
    assert db.query(AgentToolCall).count() == 2


def test_legacy_rows_without_tool_call_id_are_allowed(db):
    """旧审计行没有 tool_call_id；SQLite 唯一索引把 NULL 视为互不相等，不能因此迁移失败。"""
    db.add(_row("rec-1", "s1", None))
    db.add(_row("rec-2", "s1", None))
    db.commit()
    assert db.query(AgentToolCall).count() == 2
