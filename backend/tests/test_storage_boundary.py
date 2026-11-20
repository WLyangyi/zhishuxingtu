# -*- coding: utf-8 -*-
"""任务 0.2:断流 409 + checkpoint_id 重放(TDD)。

bug:前端 abort SSE 后,snapshot.next 非空但无真实 interrupt,下一轮被 409 误挡。
修法:409 判断改看 snapshot.tasks[*].interrupts;无 interrupt 的 pending next
用 turn_start_checkpoint_id 作 config 重放,丢弃未完成运行,追加新问题。
"""
import os
import sqlite3
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain_core.messages import AIMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.api.routes.agent import _resolve_stream_config
from app.services.agent import nodes
from app.services.agent.graph import build_input
from app.services.agent.nodes import agent_step, intent_classify, output
from app.services.agent.state import AgentState


def _task(interrupts=()):
    return SimpleNamespace(interrupts=list(interrupts))


def _interrupt():
    return SimpleNamespace(value={"type": "approval_required"})


def _snapshot(next_nodes=(), tasks=(), values=None, checkpoint_id="cp-1"):
    ns = SimpleNamespace()
    ns.next = next_nodes
    ns.tasks = tasks
    ns.values = values or {}
    ns.checkpoint_id = checkpoint_id
    return ns


# ---------- 层1:判断逻辑 + config 写法 ----------

def test_resolve_blocks_on_real_interrupt():
    """有真实 interrupt(tasks[*].interrupts 非空)→ blocked,路由层 409。"""
    snap = _snapshot(next_nodes=("execute_tool",), tasks=[_task([_interrupt()])])
    config, mode = _resolve_stream_config(snap, "sid")
    assert mode == "blocked"
    assert config is None


def test_resolve_replays_pending_without_interrupt():
    """无 interrupt 的 pending next → replay,用 turn_start_checkpoint_id 作 config。"""
    snap = _snapshot(
        next_nodes=("agent_step",),
        tasks=[_task([])],
        values={"turn_start_checkpoint_id": "cp-start"},
    )
    config, mode = _resolve_stream_config(snap, "sid")
    assert mode == "replay"
    assert config == {"configurable": {"thread_id": "sid", "checkpoint_id": "cp-start"}}


def test_resolve_normal_when_no_pending():
    """无 pending next → normal,用默认 config。"""
    snap = _snapshot(next_nodes=(), tasks=[])
    config, mode = _resolve_stream_config(snap, "sid")
    assert mode == "normal"
    assert config == {"configurable": {"thread_id": "sid"}}


# ---------- 层2:断流重放集成(真实 SqliteSaver) ----------

def _build_graph(checkpointer):
    g = StateGraph(AgentState)
    g.add_node("intent_classify", intent_classify)
    g.add_node("agent_step", agent_step)
    g.add_node("output", output)
    g.add_edge(START, "intent_classify")
    g.add_edge("intent_classify", "agent_step")
    g.add_edge("agent_step", "output")
    g.add_edge("output", END)
    return g.compile(checkpointer=checkpointer)


def test_replay_config_answers_new_question(monkeypatch):
    """断流后用 turn_start_checkpoint_id 作 config 重放,新问题被正确回答。
    锁住重放 config 写法:{"configurable":{"thread_id":...,"checkpoint_id":...}}。
    (abort 模拟用 next(it) 部分消费会触发 SqliteSaver 跨线程 put 崩溃,故用完整
    重放验证重放效果;409 判断与 replay 决策由 test_resolve_* 单测覆盖。)"""
    answer_holder = {"value": ""}

    class _FakeLLM:
        def invoke(self, msgs):
            return AIMessage(content=answer_holder["value"])

    class _FakeProvider:
        def bind_tools(self, tools):
            return _FakeLLM()

    monkeypatch.setattr(nodes.settings, "FORCE_INTENT", "knowledge")
    monkeypatch.setattr(nodes, "get_deepseek_provider", lambda: _FakeProvider())
    monkeypatch.setattr(nodes, "get_preference_context", lambda *a, **k: "")

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path, check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    try:
        graph = _build_graph(saver)
        sid = "replay-thread"
        config = {"configurable": {"thread_id": sid}}

        # 第一轮完整跑,建立 checkpoint 历史,拿到 checkpoint_id
        answer_holder["value"] = "第一轮答案"
        list(graph.stream(build_input("第一轮问题", sid, "u1"), config=config))
        snap = graph.get_state(config)
        cp_id = snap.config["configurable"].get("checkpoint_id")
        assert cp_id

        # 模拟断流后重放:用 turn_start_checkpoint_id 作 config 重放新问题
        answer_holder["value"] = "第二轮答案"
        rconfig = {"configurable": {"thread_id": sid, "checkpoint_id": cp_id}}
        result = list(graph.stream(build_input("第二轮问题", sid, "u1"), config=rconfig))
        answer = result[-1]["output"]["answer"]
        assert answer == "第二轮答案"
    finally:
        conn.close()
        os.unlink(path)
