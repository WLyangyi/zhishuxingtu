# -*- coding: utf-8 -*-
"""三期 3.1:operation_id 业务幂等键 + planned 行登记 + query_result 核对(TDD)。

验证:
- compute_operation_id 对相同参数确定、不同参数不同、与 tool_call_id 解耦
- register_planned 写 planned 行(operation_id + 参数摘要 + status=planned),幂等不产生新行
- update_result 流转 succeeded/failed
- query_result / find_succeeded_by_operation 按 operation_id 核对
- list_planned_by_session 列出断流后待核对的 planned 行
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.agent_session import AgentToolCall
from app.services.agent.tool_ops import (
    STATUS_FAILED,
    STATUS_PLANNED,
    STATUS_SUCCEEDED,
    compute_operation_id,
    find_succeeded_by_operation,
    list_planned_by_session,
    query_result,
    register_planned,
    update_result,
)


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


def test_operation_id_deterministic_for_same_args():
    op1 = compute_operation_id("s1", "search_notes", {"query": "vue"})
    op2 = compute_operation_id("s1", "search_notes", {"query": "vue"})
    assert op1 == op2


def test_operation_id_differs_for_different_args_or_tool():
    a = compute_operation_id("s1", "search_notes", {"query": "vue"})
    b = compute_operation_id("s1", "search_notes", {"query": "react"})
    c = compute_operation_id("s1", "get_note", {"query": "vue"})
    d = compute_operation_id("s2", "search_notes", {"query": "vue"})
    assert len({a, b, c, d}) == 4


def test_operation_id_independent_of_tool_call_id():
    """业务键只看 session+tool+args,与模型侧 tool_call_id 无关。"""
    op = compute_operation_id("s1", "search_notes", {"query": "vue"})
    assert op.startswith("op:s1:search_notes:")


def test_register_planned_writes_planned_row(db):
    op = compute_operation_id("s1", "search_notes", {"query": "vue"})
    row = register_planned("s1", "call_1", "search_notes", {"query": "vue"}, op, db=db)
    assert row.status == STATUS_PLANNED
    assert row.operation_id == op
    assert row.tool_name == "search_notes"
    assert "vue" in row.args_json
    assert row.result_json is None


def test_register_planned_idempotent_no_new_row(db):
    op = compute_operation_id("s1", "search_notes", {"query": "vue"})
    register_planned("s1", "call_1", "search_notes", {"query": "vue"}, op, db=db)
    register_planned("s1", "call_1", "search_notes", {"query": "vue"}, op, db=db)
    assert db.query(AgentToolCall).count() == 1


def test_update_result_transitions_succeeded(db):
    op = compute_operation_id("s1", "search_notes", {"query": "vue"})
    register_planned("s1", "call_1", "search_notes", {"query": "vue"}, op, db=db)
    update_result("s1", "call_1", STATUS_SUCCEEDED, '{"docs":[]}', 120, db=db)
    row = db.query(AgentToolCall).filter_by(tool_call_id="call_1").first()
    assert row.status == STATUS_SUCCEEDED
    assert row.result_json == '{"docs":[]}'
    assert row.latency_ms == 120


def test_update_result_transitions_failed(db):
    op = compute_operation_id("s1", "search_notes", {"query": "vue"})
    register_planned("s1", "call_1", "search_notes", {"query": "vue"}, op, db=db)
    update_result("s1", "call_1", STATUS_FAILED, '{"error":"x"}', 10, db=db)
    row = db.query(AgentToolCall).filter_by(tool_call_id="call_1").first()
    assert row.status == STATUS_FAILED


def test_query_result_by_operation_id(db):
    op = compute_operation_id("s1", "search_notes", {"query": "vue"})
    register_planned("s1", "call_1", "search_notes", {"query": "vue"}, op, db=db)
    update_result("s1", "call_1", STATUS_SUCCEEDED, '{"docs":[]}', 50, db=db)
    res = query_result("s1", op, db=db)
    assert res is not None
    assert res["status"] == STATUS_SUCCEEDED
    assert res["tool_name"] == "search_notes"


def test_query_result_none_when_absent(db):
    assert query_result("s1", "op:nonexistent", db=db) is None


def test_find_succeeded_only_returns_succeeded(db):
    op = compute_operation_id("s1", "search_notes", {"query": "vue"})
    register_planned("s1", "call_1", "search_notes", {"query": "vue"}, op, db=db)
    # 仍是 planned,未成功
    assert find_succeeded_by_operation("s1", op, db=db) is None
    update_result("s1", "call_1", STATUS_SUCCEEDED, '{"docs":[]}', 1, db=db)
    assert find_succeeded_by_operation("s1", op, db=db) is not None


def test_list_planned_by_session_returns_pending(db):
    op1 = compute_operation_id("s1", "search_notes", {"query": "vue"})
    op2 = compute_operation_id("s1", "get_note", {"id": "n1"})
    register_planned("s1", "call_1", "search_notes", {"query": "vue"}, op1, db=db)
    register_planned("s1", "call_2", "get_note", {"id": "n1"}, op2, db=db)
    # call_2 已成功,call_1 仍 planned
    update_result("s1", "call_2", STATUS_SUCCEEDED, '{"id":"n1"}', 5, db=db)
    planned = list_planned_by_session("s1", db=db)
    assert len(planned) == 1
    assert planned[0]["operation_id"] == op1
    assert planned[0]["tool_call_id"] == "call_1"
