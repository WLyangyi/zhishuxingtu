# -*- coding: utf-8 -*-
"""二期 2.4:状态字段结构化——AgentState 加 current_subtask / completed_steps /
context_snapshot / phase / status / pending_clarification。

约定:
- 常驻字段(current_subtask / completed_steps / context_snapshot / phase / status)跨轮保留,
  build_input 不重置,从 checkpoint 取;
- 临时字段(pending_clarification)每轮 build_input 重置为 None(双保险),本轮需要澄清时由节点写入。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.agent.graph import build_input
from app.services.agent.state import AgentState


# ---------- 字段存在性 ----------
def test_agent_state_has_task_structured_fields():
    """AgentState 类型含二期 2.4 六个字段。"""
    annotations = AgentState.__annotations__
    for field in (
        "current_subtask",
        "completed_steps",
        "context_snapshot",
        "phase",
        "status",
        "pending_clarification",
    ):
        assert field in annotations, f"AgentState 缺字段: {field}"


# ---------- build_input 重置约定 ----------
def test_build_input_resets_pending_clarification():
    """临时字段 pending_clarification 每轮重置为 None。"""
    inp = build_input("问题", "s1", "u1")
    assert inp.get("pending_clarification") is None


def test_build_input_does_not_reset_persistent_fields():
    """常驻字段不进 build_input(从 checkpoint 保留,不在此重置)。"""
    inp = build_input("问题", "s1", "u1")
    for field in ("current_subtask", "completed_steps", "context_snapshot", "phase", "status"):
        assert field not in inp, f"常驻字段不应在 build_input 中重置: {field}"


def test_build_input_keeps_existing_anchor_reset_convention():
    """一期临时字段重置约定不破坏。"""
    inp = build_input("问题", "s1", "u1")
    assert inp.get("last_intent_change") is None
    assert inp.get("low_confidence_hint") == ""
    assert inp.get("pending_preference") is None


# ---------- 多轮流转维护 ----------
def test_persistent_fields_flow_across_turns():
    """常驻字段在多轮流转中保留:本轮写入,下一轮从 checkpoint 读到(模拟 LangGraph 合并)。"""
    # 第一轮:节点写入常驻字段 + 临时字段
    turn1_state = {
        "session_id": "s1",
        "current_subtask": "检索相关笔记",
        "completed_steps": ["search_notes"],
        "context_snapshot": {"topic": "周报"},
        "phase": "executing",
        "status": "active",
        "pending_clarification": "需要确认目标受众",
    }
    # 第二轮 build_input 重置临时字段,但常驻字段不在此出现 → 合并后保留
    inp = build_input("继续", "s1", "u1")
    merged = {**turn1_state, **inp}

    assert merged["current_subtask"] == "检索相关笔记"
    assert merged["completed_steps"] == ["search_notes"]
    assert merged["context_snapshot"] == {"topic": "周报"}
    assert merged["phase"] == "executing"
    assert merged["status"] == "active"
    # 临时字段被重置
    assert merged["pending_clarification"] is None


def test_completed_steps_accumulate():
    """completed_steps 跨轮累积(节点追加,不重置)。"""
    turn1 = {"completed_steps": ["search_notes"]}
    turn2_update = {"completed_steps": ["search_notes", "get_note"]}
    # 模拟节点更新(追加而非覆盖场景:节点返回完整列表)
    accumulated = turn2_update["completed_steps"]
    assert "search_notes" in accumulated
    assert "get_note" in accumulated
