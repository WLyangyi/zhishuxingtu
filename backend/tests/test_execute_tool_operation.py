# -*- coding: utf-8 -*-
"""三期 3.1+3.3:execute_tool 集成——planned 行登记 + 写工具业务级幂等(TDD)。

验证 execute_tool 节点:
- 调用工具前写 planned 行(operation_id + 参数摘要),执行后更新 succeeded/failed
- create_note 业务级幂等:operation_id 已成功则跳过重复执行,复用缓存结果(不调 _call_tool/interrupt)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from langchain_core.messages import AIMessage

import app.services.agent.tool_ops as tool_ops
from app.models.agent_session import AgentToolCall
from app.models.note import Note
from app.services.agent.nodes import execute_tool
from app.services.agent.tool_ops import (
    STATUS_FAILED,
    STATUS_SUCCEEDED,
    compute_operation_id,
    query_result,
    register_planned,
    update_result,
)


@pytest.fixture()
def engine(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AgentToolCall.__table__.create(engine)
    Note.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    # 让 tool_ops 的 SessionLocal 每次返回新 session(共享同一内存库)
    monkeypatch.setattr(tool_ops, "SessionLocal", Session)
    yield engine
    engine.dispose()


def _state(tool_name, args, call_id="call_1", session_id="s1"):
    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": tool_name, "args": args, "id": call_id}],
            )
        ],
        "session_id": session_id,
        "tool_calls_log": [],
        "documents": [],
        "searched_queries": [],
        "thoughts": [],
    }


def _row(engine, tool_call_id="call_1"):
    s = sessionmaker(bind=engine)()
    try:
        return s.query(AgentToolCall).filter_by(tool_call_id=tool_call_id).first()
    finally:
        s.close()


def test_execute_tool_writes_planned_then_succeeded(engine, monkeypatch):
    calls = []

    def fake_call(fn, name, args, state, **kw):
        calls.append(name)
        return "success", '{"tags": []}'

    monkeypatch.setattr("app.services.agent.nodes._call_tool", fake_call)

    out = execute_tool(_state("list_tags", {}))

    assert "list_tags" in calls  # 工具被调用
    row = _row(engine)
    assert row is not None
    assert row.operation_id is not None
    assert row.operation_id.startswith("op:s1:list_tags:")
    assert row.status == STATUS_SUCCEEDED
    assert row.result_json == '{"tags": []}'
    # ToolMessage 正常产出
    assert len(out["messages"]) == 1


def test_execute_tool_writes_failed_on_error(engine, monkeypatch):
    def fake_call(fn, name, args, state, **kw):
        return "error", '{"error": "boom"}'

    monkeypatch.setattr("app.services.agent.nodes._call_tool", fake_call)

    execute_tool(_state("list_tags", {}))

    row = _row(engine)
    assert row.status == STATUS_FAILED


def test_create_note_idempotent_skips_execution(engine, monkeypatch):
    # 预置一条已成功的 create_note 行 + 副作用(Note 已落库)
    op = compute_operation_id("s1", "create_note", {"title": "T", "content": "C"})
    s = sessionmaker(bind=engine)()
    register_planned("s1", "call_1", "create_note", {"title": "T", "content": "C"}, op, db=s)
    update_result("s1", "call_1", STATUS_SUCCEEDED, '{"id": "n1"}', 50, db=s)
    s.add(Note(id="n1", title="T", content="C", user_id="u1", idempotency_key="agent:s1:call_1"))
    s.commit()
    s.close()

    calls = []

    def fake_call(fn, name, args, state, **kw):
        calls.append(name)
        return "success", '{"id": "n2"}'

    monkeypatch.setattr("app.services.agent.nodes._call_tool", fake_call)

    state = _state("create_note", {"title": "T", "content": "C"})
    state["current_agent"] = "chat"  # 非 note_write,跳过查重前置
    state["user_id"] = "u1"
    out = execute_tool(state)

    assert calls == []  # 幂等命中(status=succeeded 且 Note 已落库),未调用 _call_tool
    row = _row(engine)
    assert row.status == STATUS_SUCCEEDED  # 仍是已成功,未被覆盖
    # ToolMessage 复用缓存结果
    assert "n1" in out["messages"][-1].content


# ---------- 三期3.2:pending_tools 四态映射 ----------

def test_execute_tool_pending_tools_succeeded(engine, monkeypatch):
    """planned→succeeded:成功执行后 pending_tools 条目记 succeeded。"""

    def fake_call(fn, name, args, state, **kw):
        return "success", '{"tags": []}'

    monkeypatch.setattr("app.services.agent.nodes._call_tool", fake_call)
    out = execute_tool(_state("list_tags", {}))
    pt = out["pending_tools"]
    assert len(pt) == 1
    assert pt[0]["status"] == "succeeded"
    assert pt[0]["operation_id"].startswith("op:s1:list_tags:")
    assert pt[0]["tool_name"] == "list_tags"
    assert pt[0]["result"] == '{"tags": []}'


def test_execute_tool_pending_tools_failed(engine, monkeypatch):
    """planned→failed:错误执行后 pending_tools 条目记 failed。"""

    def fake_call(fn, name, args, state, **kw):
        return "error", '{"error": "boom"}'

    monkeypatch.setattr("app.services.agent.nodes._call_tool", fake_call)
    out = execute_tool(_state("list_tags", {}))
    pt = out["pending_tools"]
    assert len(pt) == 1
    assert pt[0]["status"] == "failed"


def test_pending_tools_unknown_state_via_query_result(engine):
    """unknown 态:断流后 DB 仍 planned 无结果,query_result 返回 planned 供恢复核对。"""
    op = compute_operation_id("s1", "search_notes", {"query": "vue"})
    s = sessionmaker(bind=engine)()
    register_planned("s1", "call_1", "search_notes", {"query": "vue"}, op, db=s)
    s.close()
    res = query_result("s1", op)
    assert res is not None
    assert res["status"] == "planned"  # unknown:副作用未确认
    assert res["result"] is None


def test_build_input_resets_pending_tools():
    """pending_tools 是本轮临时字段,build_input 每轮重置为空。"""
    from app.services.agent.graph import build_input

    out = build_input("q", "s1", "u1")
    assert out["pending_tools"] == []


# ---------- 三期3.3:业务级幂等键(跨 tool_call_id) ----------

def test_business_idempotency_across_different_tool_call_id(engine, monkeypatch):
    """业务键只看 session+tool+args:重放用不同 tool_call_id 但同参数,
    仍命中同一 operation_id,跳过重复执行(不产生重复副作用)。"""
    op = compute_operation_id("s1", "create_note", {"title": "T", "content": "C"})
    # 第一次:tool_call_id=call_1,已成功 + 副作用(Note 已落库)
    s = sessionmaker(bind=engine)()
    register_planned("s1", "call_1", "create_note", {"title": "T", "content": "C"}, op, db=s)
    update_result("s1", "call_1", STATUS_SUCCEEDED, '{"id": "n1"}', 50, db=s)
    s.add(Note(id="n1", title="T", content="C", user_id="u1", idempotency_key="agent:s1:call_1"))
    s.commit()
    s.close()

    calls = []

    def fake_call(fn, name, args, state, **kw):
        calls.append(name)
        return "success", '{"id": "n2"}'

    monkeypatch.setattr("app.services.agent.nodes._call_tool", fake_call)

    # 第二次:不同 tool_call_id=call_2,但同参数 → 同一 operation_id → 幂等跳过
    state = _state("create_note", {"title": "T", "content": "C"}, call_id="call_2")
    state["current_agent"] = "chat"
    state["user_id"] = "u1"
    out = execute_tool(state)

    assert calls == []  # 业务键命中,未调用 _call_tool
    # call_2 行被登记为 planned 但未执行?不——幂等命中时不写 planned 行,
    # 仅 pending_tools 记 succeeded(复用缓存)
    assert out["pending_tools"][0]["status"] == "succeeded"
    assert out["pending_tools"][0]["operation_id"] == op
    # 原 call_1 行未被改动
    row1 = _row(engine, "call_1")
    assert row1.status == STATUS_SUCCEEDED
