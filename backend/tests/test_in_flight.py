# -*- coding: utf-8 -*-
"""任务 0.3:并发 in-flight 标记(TDD)。

同 thread 并发写返回 409;流 finally 清理不残留;TTL 兜底;
检查顺序:in-flight → 真实 interrupt → 无 interrupt 重放。
"""
import asyncio
import os
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import HTTPException

from app.api.routes import agent as agent_route
from app.api.routes.agent import (
    _IN_FLIGHT,
    _IN_FLIGHT_TTL,
    _acquire_in_flight,
    _release_in_flight,
)


def test_first_acquire_succeeds_second_blocked():
    _IN_FLIGHT.clear()
    assert _acquire_in_flight("t1") is True
    assert _acquire_in_flight("t1") is False


def test_release_clears_marker():
    _IN_FLIGHT.clear()
    _acquire_in_flight("t1")
    _release_in_flight("t1")
    assert "t1" not in _IN_FLIGHT
    assert _acquire_in_flight("t1") is True


def test_ttl_expiry_allows_reacquire():
    _IN_FLIGHT.clear()
    _acquire_in_flight("t1")
    _IN_FLIGHT["t1"] = time.time() - _IN_FLIGHT_TTL - 1
    assert _acquire_in_flight("t1") is True


def test_inflight_checked_before_interrupt(monkeypatch):
    """检查顺序:in-flight 命中优先 409,不走到 interrupt/重放判断。"""
    _IN_FLIGHT.clear()
    _acquire_in_flight("sid")  # 占用,模拟并发

    def _boom(snapshot, session_id):
        raise AssertionError("_resolve_stream_config 不应被调用(in-flight 应优先)")

    monkeypatch.setattr(agent_route, "_resolve_stream_config", _boom)
    monkeypatch.setattr(
        agent_route,
        "_get_or_create_session",
        lambda *a, **k: SimpleNamespace(
            id="sid", title="t", total_tokens=0, total_cost_cny=0.0
        ),
    )
    user = SimpleNamespace(id="u1")
    db = SimpleNamespace()

    with pytest.raises(HTTPException) as ei:
        asyncio.run(
            agent_route.agent_chat_stream(
                "q", session_id="sid", history=None, current_user=user, db=db
            )
        )
    assert ei.value.status_code == 409


def test_stream_finally_releases_inflight(monkeypatch):
    """_stream_graph 流结束后,in-flight 标记被 finally 清理,不残留。"""
    _IN_FLIGHT.clear()
    _acquire_in_flight("t1")
    assert "t1" in _IN_FLIGHT

    class _FakeGraph:
        def stream(self, graph_input, config=None):
            return iter([])

        def get_state(self, config):
            return SimpleNamespace(values={}, next=())

    monkeypatch.setattr(agent_route, "get_graph", lambda: _FakeGraph())
    monkeypatch.setattr(
        agent_route,
        "build_stream_config",
        lambda sid, user_id=None: {"configurable": {"thread_id": sid}},
    )
    session = SimpleNamespace(
        id="t1", agent_route="", total_tokens=0, total_cost_cny=0.0, updated_at=None
    )
    db = SimpleNamespace(add=lambda *a: None, commit=lambda: None)

    list(
        agent_route._stream_graph(
            db, {"messages": [], "question": "q"}, session, "u1",
            in_flight_thread_id="t1",
        )
    )
    assert "t1" not in _IN_FLIGHT
