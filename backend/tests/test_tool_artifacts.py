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
from langchain_core.messages import AIMessage
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


def _execute_tool(monkeypatch, name, args, result):
    class FakeTool:
        def invoke(self, _args):
            return result

    fake = FakeTool()
    fake.name = name
    monkeypatch.setitem(nodes.TOOL_MAP, name, fake)
    state = _state(
        messages=[AIMessage(content="", tool_calls=[
            {"name": name, "args": args, "id": "call_1", "type": "tool_call"}])],
        thoughts=[],
        tool_calls_log=[],
        documents=[],
        searched_queries=[],
    )
    return nodes.execute_tool(state)


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


def test_web_search_summary_under_8000_not_offloaded(db_factory, monkeypatch):
    """行为15：5 条完整 summary(≈5k)在 web_search 专属 8000 阈值内联，不常态 offload，
    让模型直接读到全文摘要而非压缩预览。"""
    monkeypatch.setattr("app.db.session.SessionLocal", db_factory)
    result = json.dumps(
        [{"title": f"t{i}", "url": f"https://e.com/{i}", "snippet": "s" * 900,
          "rerank_score": 2.0, "authority": 3} for i in range(5)],
        ensure_ascii=False,
    )
    assert 4000 < len(result) <= 8000

    out = _execute_tool(monkeypatch, "web_search", {"query": "q"}, result)

    assert out["messages"][-1].content == result
    assert "[已压缩]" not in out["messages"][-1].content
    db = db_factory()
    try:
        assert db.query(AgentToolArtifact).count() == 0
    finally:
        db.close()


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


def test_compress_web_list_keeps_url_and_quality_fields():
    """行为15：联网检索 list 压缩白名单须保 url/rerank_score/authority/date/site_name，
    否则预览丢 url→模型无法据摘要选优后 web_fetch(url)，编排断链。"""
    raw = json.dumps(
        [{"title": "t", "url": "https://e.com", "snippet": "s" * 900,
          "rerank_score": 2.0, "authority": 3, "date": "2026-01-01",
          "site_name": "SN", "noise": "drop-me"}],
        ensure_ascii=False,
    )
    item = json.loads(artifacts.compress_result(raw))[0]
    assert item["url"] == "https://e.com"
    assert item["rerank_score"] == 2.0
    assert item["authority"] == 3
    assert item["date"] == "2026-01-01"
    assert item["site_name"] == "SN"
    assert "noise" not in item
    assert len(item["snippet"]) == artifacts.SNIPPET_KEEP


def test_web_search_over_8000_compress_keeps_url(db_factory, monkeypatch):
    """行为15：偶发超 8000 的 web_search list 仍压缩，但白名单兜底保 url/rerank_score。"""
    monkeypatch.setattr("app.db.session.SessionLocal", db_factory)
    result = json.dumps(
        [{"title": f"t{i}", "url": f"https://e.com/{i}", "snippet": "s" * 1500,
          "rerank_score": 2.5, "authority": 4, "date": "2026-01-01", "site_name": "SN"}
         for i in range(6)],
        ensure_ascii=False,
    )
    assert len(result) > 8000

    out = _execute_tool(monkeypatch, "web_search", {"query": "q"}, result)
    content = out["messages"][-1].content

    assert "artifact_id=" in content
    preview = json.loads(content.split("\n\n[已压缩]")[0])
    assert preview[0]["url"] == "https://e.com/0"
    assert preview[0]["rerank_score"] == 2.5
    assert preview[0]["authority"] == 4
    db = db_factory()
    try:
        row = db.query(AgentToolArtifact).one()
        assert row.length == len(result)
    finally:
        db.close()


def test_web_fetch_offloaded_keeps_url_and_full_artifact(db_factory, monkeypatch):
    """行为15：web_fetch 长文 dict 走默认 4000 阈值 offload，预览保 url、content 截 1200，
    全文完整落库（length==原文），可凭 artifact_id 分页取回。"""
    monkeypatch.setattr("app.db.session.SessionLocal", db_factory)
    content = "# 标题\n" + "正" * 12000
    result = json.dumps(
        {"title": "T", "url": "https://e.com/page", "content": content},
        ensure_ascii=False,
    )
    assert len(result) > 4000

    out = _execute_tool(
        monkeypatch, "web_fetch", {"url": "https://e.com/page"}, result
    )
    content = out["messages"][-1].content

    assert "artifact_id=" in content
    preview = json.loads(content.split("\n\n[已压缩]")[0])
    assert preview["url"] == "https://e.com/page"
    assert len(preview["content"]) == artifacts.NOTE_BODY_KEEP
    db = db_factory()
    try:
        row = db.query(AgentToolArtifact).first()
        assert row.length == len(result)
    finally:
        db.close()


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
