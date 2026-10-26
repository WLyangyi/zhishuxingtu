# -*- coding: utf-8 -*-
"""Phase 4:MCP 工具权限三级 + 注解 + dry-run。

为什么这三件事要单测:它们全是"默认关"的安全阀——写权限、dry-run、未登记工具。
安全阀最容易的坏法不是"没写",而是"写了但默认是开的",所以每条都要钉住
"默认拒绝"这一侧的行为。
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import mcp_server
from app.services.mcp_server import create_mcp_server, mcp_create_note_dry_run
from app.services.tools.permissions import (
    DANGEROUS,
    READ,
    policy_for,
    should_register_on_mcp,
    tool_annotations,
)


# ---------- 权限表 ----------
def test_unregistered_tool_is_treated_as_dangerous():
    policy = policy_for("delete_everything")
    assert policy.level == DANGEROUS
    assert policy.mcp_exposed is False
    assert should_register_on_mcp(
        "delete_everything", enable_write=True, has_write_user=True
    ) is False


def test_session_bound_tool_not_exposed_even_if_read():
    assert policy_for("read_tool_artifact").level == READ
    assert should_register_on_mcp(
        "read_tool_artifact", enable_write=True, has_write_user=True
    ) is False


def test_write_tool_requires_switch_and_user():
    assert should_register_on_mcp("create_note", enable_write=False, has_write_user=True) is False
    assert should_register_on_mcp("create_note", enable_write=True, has_write_user=False) is False
    assert should_register_on_mcp("create_note", enable_write=True, has_write_user=True) is True


def test_annotations_reflect_tool_semantics():
    read_ann = tool_annotations("search_notes")
    assert read_ann["readOnlyHint"] is True
    assert read_ann["idempotentHint"] is True
    assert read_ann["openWorldHint"] is False

    assert tool_annotations("web_search")["openWorldHint"] is True

    write_ann = tool_annotations("create_note")
    assert write_ann["readOnlyHint"] is False
    assert write_ann["idempotentHint"] is False
    # 写入不是破坏性操作,不能被客户端当删除处理
    assert write_ann["destructiveHint"] is False

    assert tool_annotations("delete_everything")["destructiveHint"] is True


# ---------- dry-run ----------
def test_dry_run_returns_preview_and_touches_no_db(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("dry-run 不应访问数据库")

    monkeypatch.setattr("app.db.session.SessionLocal", _boom)

    out = json.loads(
        mcp_create_note_dry_run(title="标题", content="正文" * 500, folder_id="f1")
    )
    assert out["dry_run"] is True
    assert out["would_create"]["title"] == "标题"
    assert len(out["would_create"]["content_preview"]) == 500
    assert "id" not in out


# ---------- 注册闸门 ----------
def _registered_names():
    tools = asyncio.run(create_mcp_server().list_tools())
    return {t.name: t for t in tools}


def test_default_server_exposes_only_read_tools(monkeypatch):
    monkeypatch.setattr(mcp_server.settings, "MCP_ENABLE_WRITE", False)
    monkeypatch.setattr(mcp_server.settings, "MCP_WRITE_USER_ID", "")

    tools = _registered_names()
    assert set(tools) == {
        "search_notes",
        "get_note",
        "get_graph_neighbors",
        "list_tags",
        "list_folders",
        "web_search",
    }
    assert tools["search_notes"].annotations.readOnlyHint is True


def test_write_tool_registered_only_with_switch_and_user(monkeypatch):
    monkeypatch.setattr(mcp_server.settings, "MCP_ENABLE_WRITE", True)
    monkeypatch.setattr(mcp_server.settings, "MCP_WRITE_USER_ID", "u1")
    monkeypatch.setattr(mcp_server.settings, "MCP_DRY_RUN", True)

    tools = _registered_names()
    assert "create_note" in tools
    assert tools["create_note"].annotations.readOnlyHint is False


def test_write_switch_without_user_stays_closed(monkeypatch):
    monkeypatch.setattr(mcp_server.settings, "MCP_ENABLE_WRITE", True)
    monkeypatch.setattr(mcp_server.settings, "MCP_WRITE_USER_ID", "")

    assert "create_note" not in _registered_names()
