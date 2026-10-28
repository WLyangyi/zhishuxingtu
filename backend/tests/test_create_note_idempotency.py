# -*- coding: utf-8 -*-
"""create_note 幂等键:同一 tool_call 被重放时不重复落库。

对应 Phase 4 验收标准「重放同一请求不重复写」。
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.note import Note
from app.services.tools import write_tools
from app.services.tools.context import (
    ToolContext,
    reset_tool_context,
    set_tool_context,
)


@pytest.fixture()
def db_factory(monkeypatch):
    engine = create_engine("sqlite://")
    Note.__table__.create(engine)
    factory = sessionmaker(bind=engine)

    # 屏蔽 embedding / BM25 写入:单测不触发网络,也不依赖全局单例状态
    import app.db.session as db_session
    import app.services.bm25_service as bm25_mod
    import app.services.vector_store_adapter as vsa_mod

    class _DummyBM25:
        is_ready = False

    monkeypatch.setattr(db_session, "SessionLocal", factory)
    monkeypatch.setattr(vsa_mod, "get_vector_store_adapter", lambda: None)
    monkeypatch.setattr(bm25_mod, "get_bm25_service", lambda: _DummyBM25())

    try:
        yield factory
    finally:
        engine.dispose()


def _call(**ctx_kwargs) -> dict:
    token = set_tool_context(ToolContext(user_id="u1", session_id="s1", **ctx_kwargs))
    try:
        raw = write_tools.create_note.invoke({"title": "幂等测试", "content": "正文"})
    finally:
        reset_tool_context(token)
    return json.loads(raw)


def _count(factory) -> int:
    db = factory()
    try:
        return db.query(Note).count()
    finally:
        db.close()


def test_replay_same_tool_call_writes_once(db_factory):
    first = _call(tool_call_id="call_1")
    second = _call(tool_call_id="call_1")

    assert first.get("idempotent_replay") is None
    assert second.get("idempotent_replay") is True
    assert first["id"] == second["id"]
    assert _count(db_factory) == 1


def test_different_tool_call_writes_twice(db_factory):
    first = _call(tool_call_id="call_1")
    second = _call(tool_call_id="call_2")

    assert first["id"] != second["id"]
    assert _count(db_factory) == 2


def test_missing_tool_call_id_falls_back_to_no_idempotency(db_factory):
    # MCP 直调没有 tool_call_id,保持原有行为:两次都是新写入
    first = _call()
    second = _call()

    assert first["id"] != second["id"]
    assert _count(db_factory) == 2
