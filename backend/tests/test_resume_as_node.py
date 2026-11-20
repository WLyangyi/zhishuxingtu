# -*- coding: utf-8 -*-
"""任务 1.8:/resume 合并——graph.update_state 的 as_node 取值对 pending interrupt 恢复的影响(TDD)。

关键结论(实测):update_state(as_node=...) 会清空 pending interrupt 的 tasks,
因此在 resume 之前做 update_state 会破坏中断恢复。正确做法是 resume 流正常完成后
再 update_state 合并锚点(此时图已在 END,不破坏任何东西)。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.services.agent.state import AgentState


def _build_interrupt_graph():
    def _interrupt_node(state):
        val = interrupt({"type": "approval_required"})
        return {"answer": f"resumed-approved={val.get('approved')}"}

    g = StateGraph(AgentState)
    g.add_node("interrupt_node", _interrupt_node)
    g.add_edge(START, "interrupt_node")
    g.add_edge("interrupt_node", END)
    return g.compile(checkpointer=MemorySaver())


def test_update_state_before_resume_clears_interrupt():
    """坑位验证:resume 前 update_state(as_node) 会清空 pending interrupt,resume 失效。"""
    graph = _build_interrupt_graph()
    config = {"configurable": {"thread_id": "r-before"}}
    list(graph.stream({"messages": [], "question": "q"}, config=config))
    snap = graph.get_state(config)
    assert snap.next  # 有 pending interrupt

    # resume 前 update_state → 清空 interrupt
    graph.update_state(
        config,
        {"core_intent": {"goal": "g", "constraints": {}, "acceptance_criteria": []}, "intent_version": 1},
        as_node="interrupt_node",
    )
    snap_after_update = graph.get_state(config)
    assert not snap_after_update.next  # interrupt 被清空
    # resume 无法恢复(无 pending interrupt),答案不产出
    list(graph.stream(Command(resume={"approved": True, "reason": ""}), config=config))
    snap2 = graph.get_state(config)
    assert snap2.values.get("answer") is None  # resume 失效,无答案


def test_update_state_after_resume_preserves_anchor():
    """正确做法:resume 流完成后再 update_state(as_node) 合并锚点,不破坏恢复且锚点落 checkpoint。"""
    graph = _build_interrupt_graph()
    config = {"configurable": {"thread_id": "r-after"}}
    list(graph.stream({"messages": [], "question": "q"}, config=config))
    assert graph.get_state(config).next  # pending interrupt

    # 先 resume(不清 interrupt),图完成
    list(graph.stream(Command(resume={"approved": True, "reason": ""}), config=config))
    snap_resumed = graph.get_state(config)
    assert not snap_resumed.next
    assert snap_resumed.values.get("answer") == "resumed-approved=True"

    # resume 之后 update_state 合并锚点(图已在 END,安全)
    graph.update_state(
        config,
        {
            "core_intent": {"goal": "合并目标", "constraints": {"tone": "正式"}, "acceptance_criteria": []},
            "intent_version": 3,
            "last_intent_change": {"change_type": "append", "source": "resume", "ts": "t"},
        },
        as_node="interrupt_node",
    )
    snap2 = graph.get_state(config)
    assert snap2.values.get("core_intent")["goal"] == "合并目标"
    assert snap2.values.get("intent_version") == 3
    assert snap2.values.get("last_intent_change")["source"] == "resume"
