# -*- coding: utf-8 -*-
"""Phase 4:工具结果 offload——大结果落库存档、消息只留压缩预览、可凭 id 取回。

覆盖三件容易退化的事:
1. 压缩必须"可继续推理"(字段投影/头尾保留),而不是把结果砍成不可用的碎片;
2. 落库失败必须退回完整结果,不能以省 token 为由丢证据;
3. 存档只能被本会话读取(跨会话越权是安全问题,不是便利问题)。
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.agent_session import AgentToolArtifact
from app.services.agent import artifacts, nodes
from app.services.tools import artifact_tools
from app.services.tools.context import (
    ToolContext,
    reset_tool_context,
    set_tool_context,
)


@pytest.fixture()
def db_factory():
    engine = create_engine("sqlite://")
    AgentToolArtifact.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    try:
        yield factory
    finally:
        engine.dispose()


def _state(**extra):
    base = {"session_id": "s1", "user_id": "u1"}
    base.update(extra)
    return base


# ---------- 消息层压缩 ----------
def test_small_result_passes_through_untouched(monkeypatch):
    called = []
    monkeypatch.setattr(nodes, "ARTIFACT_THRESHOLD_CHARS", 100)
    monkeypatch.setattr(nodes, "save_artifact", lambda *a: called.append(a))

    small = json.dumps([{"id": "n1", "title": "小结果"}], ensure_ascii=False)
    assert nodes._offload_for_message(_state(), "call_1", "search_notes", small) == small
    assert called == []


def test_large_result_replaced_by_preview_with_artifact_hint(monkeypatch):
    monkeypatch.setattr(nodes, "ARTIFACT_THRESHOLD_CHARS", 100)
    monkeypatch.setattr(nodes, "save_artifact", lambda *a: "art-1")

    large = json.dumps(
        [{"id": f"n{i}", "title": "标题" * 20, "snippet": "内容" * 40} for i in range(20)],
        ensure_ascii=False,
    )
    assert len(large) > 100
    content = nodes._offload_for_message(_state(), "call_1", "search_notes", large)

    assert len(content) < len(large)
    assert "art-1" in content
    assert "read_tool_artifact" in content
    # 预览必须仍是可解析的检索结果,模型才能继续推理
    assert json.loads(content.split("\n\n[已压缩]")[0])[0]["id"] == "n0"


def test_offload_failure_falls_back_to_full_result(monkeypatch):
    monkeypatch.setattr(nodes, "ARTIFACT_THRESHOLD_CHARS", 10)
    monkeypatch.setattr(nodes, "save_artifact", lambda *a: None)

    large = "x" * 500
    assert nodes._offload_for_message(_state(), "call_1", "get_note", large) == large


# ---------- 压缩策略 ----------
def test_compress_json_list_projects_fields_and_truncates_snippet():
    raw = json.dumps(
        [{"id": "n1", "title": "t", "snippet": "s" * 900, "noise": "drop-me"}],
        ensure_ascii=False,
    )
    squeezed = artifacts.compress_result(raw)
    item = json.loads(squeezed)[0]
    assert item["id"] == "n1"
    assert len(item["snippet"]) == artifacts.SNIPPET_KEEP
    assert "noise" not in item


def test_compress_plain_text_keeps_head_and_tail():
    raw = "HEAD" + "m" * 5000 + "TAIL"
    squeezed = artifacts.compress_result(raw)
    assert squeezed.startswith("HEAD")
    assert squeezed.endswith("TAIL")
    assert "[中间省略]" in squeezed
    assert len(squeezed) < len(raw)


# ---------- 落库与读取 ----------
def test_save_artifact_is_deterministic_and_idempotent(db_factory, monkeypatch):
    monkeypatch.setattr("app.db.session.SessionLocal", db_factory)

    first = artifacts.save_artifact("s1", "call_1", "search_notes", "body")
    second = artifacts.save_artifact("s1", "call_1", "search_notes", "body")

    assert first == second == artifacts.artifact_id("s1", "call_1")
    db = db_factory()
    try:
        assert db.query(AgentToolArtifact).count() == 1
    finally:
        db.close()


def test_read_artifact_rejects_other_session(db_factory, monkeypatch):
    monkeypatch.setattr("app.db.session.SessionLocal", db_factory)
    art_id = artifacts.save_artifact("s1", "call_1", "search_notes", "secret")

    token = set_tool_context(ToolContext(user_id="u2", session_id="s2"))
    try:
        out = json.loads(
            artifact_tools.read_tool_artifact.invoke({"artifact_id": art_id})
        )
    finally:
        reset_tool_context(token)

    assert "error" in out
    assert "content" not in out


def test_read_artifact_paginates(db_factory, monkeypatch):
    monkeypatch.setattr("app.db.session.SessionLocal", db_factory)
    body = "0123456789" * 50
    art_id = artifacts.save_artifact("s1", "call_1", "get_note", body)

    token = set_tool_context(ToolContext(user_id="u1", session_id="s1"))
    try:
        out = json.loads(
            artifact_tools.read_tool_artifact.invoke(
                {"artifact_id": art_id, "offset": 10, "limit": 20}
            )
        )
    finally:
        reset_tool_context(token)

    assert out["content"] == body[10:30]
    assert out["total_length"] == len(body)
    assert out["truncated"] is True


def test_read_artifact_requires_session_context(db_factory, monkeypatch):
    monkeypatch.setattr("app.db.session.SessionLocal", db_factory)
    art_id = artifacts.save_artifact("s1", "call_1", "get_note", "body")

    out = json.loads(artifact_tools.read_tool_artifact.invoke({"artifact_id": art_id}))
    assert "error" in out
