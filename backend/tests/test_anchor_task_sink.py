# -*- coding: utf-8 -*-
"""二期 2.2：锚点下沉 task——锚点 id 带 task 维度，切 task 时替换旧锚点，无残留双锚。

核心机制：
- state 新增 current_task_id；锚点归属键优先取 task_id，无 task 时 legacy 用 session_id。
- _sync_anchor_message 清理所有非当前锚点 id 的锚点消息（旧 task 残留），再同步当前锚点。
- 一期行为不变（无 current_task_id 时锚点 id 仍为 anchor:{session_id}）。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain_core.messages import RemoveMessage, SystemMessage

from app.services.agent.nodes import (
    anchor_message_id,
    render_anchor,
    _sync_anchor_message,
    state_anchor_key,
)


def _ci(goal="写周报", constraints=None, acceptance=None):
    return {
        "goal": goal,
        "constraints": constraints or {},
        "acceptance_criteria": acceptance or [],
    }


# ---------- 锚点归属键 ----------
def test_state_anchor_key_prefers_task_id():
    state = {"session_id": "s1", "current_task_id": "t1"}
    assert state_anchor_key(state) == "t1"


def test_state_anchor_key_legacy_uses_session_id():
    state = {"session_id": "s1"}
    assert state_anchor_key(state) == "s1"


def test_state_anchor_key_empty_when_no_session():
    assert state_anchor_key({"messages": []}) == ""


# ---------- 锚点 id 带 task 维度 ----------
def test_anchor_id_with_task():
    assert anchor_message_id("t1") == "anchor:t1"


def test_render_anchor_uses_task_id():
    ci = _ci()
    msg = render_anchor(ci, "t1")
    assert msg.id == "anchor:t1"
    assert "写周报" in msg.content


def test_render_anchor_legacy_session_id():
    ci = _ci()
    msg = render_anchor(ci, "s1")
    assert msg.id == "anchor:s1"


# ---------- 切 task 替换锚点，无残留双锚 ----------
def test_sync_removes_stale_task_anchor():
    ci = _ci()
    old_anchor = render_anchor(ci, "t_old")  # anchor:t_old
    state = {"session_id": "s1", "current_task_id": "t_new", "messages": [old_anchor]}
    updates = _sync_anchor_message(state, ci)

    remove_ids = [u.id for u in updates if isinstance(u, RemoveMessage)]
    assert "anchor:t_old" in remove_ids
    # 新 task 锚点注入
    new_anchors = [u for u in updates if isinstance(u, SystemMessage)]
    assert len(new_anchors) == 1
    assert new_anchors[0].id == "anchor:t_new"


def test_switch_task_leaves_only_new_anchor():
    """切 task 后应用 updates，通道里只剩新 task 锚点，无残留双锚。"""
    ci = _ci()
    old_anchor = render_anchor(ci, "t_old")
    state = {"session_id": "s1", "current_task_id": "t_new", "messages": [old_anchor]}
    updates = _sync_anchor_message(state, ci)

    # 模拟 add_messages 应用：RemoveMessage 删除，SystemMessage 添加
    applied = [old_anchor]
    for u in updates:
        if isinstance(u, RemoveMessage):
            applied = [m for m in applied if getattr(m, "id", "") != u.id]
        else:
            applied.append(u)

    anchors = [m for m in applied if getattr(m, "id", "").startswith("anchor:")]
    assert len(anchors) == 1
    assert anchors[0].id == "anchor:t_new"


def test_sync_multiple_stale_task_anchors_cleared():
    """历史遗留多个旧 task 锚点，切到新 task 时全部清理。"""
    ci = _ci()
    stale1 = render_anchor(ci, "t_old1")
    stale2 = render_anchor(ci, "t_old2")
    state = {"session_id": "s1", "current_task_id": "t_new", "messages": [stale1, stale2]}
    updates = _sync_anchor_message(state, ci)

    remove_ids = {u.id for u in updates if isinstance(u, RemoveMessage)}
    assert "anchor:t_old1" in remove_ids
    assert "anchor:t_old2" in remove_ids
    new_anchors = [u for u in updates if isinstance(u, SystemMessage)]
    assert len(new_anchors) == 1
    assert new_anchors[0].id == "anchor:t_new"


# ---------- 一期行为兼容（legacy 不破坏） ----------
def test_legacy_sync_unchanged():
    """无 current_task_id 时，锚点 id 仍为 anchor:{session_id}，一期行为不变。"""
    ci = _ci()
    state = {"session_id": "s1", "messages": []}
    updates = _sync_anchor_message(state, ci)
    assert len(updates) == 1
    assert isinstance(updates[0], SystemMessage)
    assert updates[0].id == "anchor:s1"


def test_legacy_sync_removes_stale_session_anchor():
    ci = _ci()
    leftover = SystemMessage(content="旧", id="anchor:s1")
    state = {"session_id": "s1", "messages": [leftover]}
    updates = _sync_anchor_message(state, _ci(goal="新目标"))
    remove_ids = [u.id for u in updates if isinstance(u, RemoveMessage)]
    assert "anchor:s1" in remove_ids
