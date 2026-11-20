# -*- coding: utf-8 -*-
"""任务 0.1:turn_start_index 裁剪修复(TDD)。

bug 根因:intent_classify 写 turn_start_index = len(messages) - 1(裁剪前完整下标),
而 agent_step 每轮用 RemoveMessage 把 _retained_window 裁掉的历史从 state.messages
删除,messages 变短;到 output/generate 的 _best_answer 用原始下标切片越界,本轮答案丢失。

修法:intent_classify 改存本轮问题 message id(turn_start_id),_best_answer 按 id
定位起点,裁剪后仍能命中本轮答案。
"""
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.services.agent import nodes
from app.services.agent.graph import build_input
from app.services.agent.nodes import _best_answer, agent_step, intent_classify, output
from app.services.agent.state import AgentState


def _state(**extra):
    base = {
        "messages": [],
        "question": "测试",
        "user_id": "u1",
        "session_id": "s1",
        "thoughts": [],
    }
    base.update(extra)
    return base


# ---------- 层1:_best_answer 按 message id 定位 ----------

def test_best_answer_locates_turn_start_by_id_after_pruning():
    """裁剪后前面消息被删,按 turn_start_id 定位本轮起点,返回本轮答案。"""
    q_id = "q-this-turn"
    msgs = [
        HumanMessage(content="本轮问题", id=q_id),
        AIMessage(content="本轮答案", id="a-this"),
    ]
    assert _best_answer(msgs, turn_start_id=q_id) == "本轮答案"


def test_best_answer_turn_start_id_skips_prior_long_answer():
    """同通道含上一轮长答案,turn_start_id 指向本轮问题,不选上一轮答案。"""
    q_id = "q2"
    msgs = [
        HumanMessage(content="上一轮问题", id="q1"),
        AIMessage(content="上一轮非常长的旧答案", id="a1"),
        HumanMessage(content="本轮问题", id=q_id),
        AIMessage(content="本轮短答案", id="a2"),
    ]
    assert _best_answer(msgs, turn_start_id=q_id) == "本轮短答案"


def test_best_answer_default_keeps_full_channel_behavior():
    """不传 turn_start_id 时保持旧行为(全通道取最长 AIMessage)。"""
    msgs = [
        HumanMessage(content="q"),
        AIMessage(content="短"),
        AIMessage(content="这是内容更长的答案"),
    ]
    assert _best_answer(msgs) == "这是内容更长的答案"


# ---------- 层1:intent_classify 三条路径写 turn_start_id ----------

def test_intent_classify_force_intent_writes_turn_start_id(monkeypatch):
    """FORCE_INTENT 旁路:写本轮问题 message id 为 turn_start_id。"""
    monkeypatch.setattr(nodes.settings, "FORCE_INTENT", "knowledge")
    msgs = [
        HumanMessage(content="旧问题", id="old-q"),
        HumanMessage(content="本轮问题", id="new-q"),
    ]
    out = intent_classify(_state(question="本轮问题", messages=msgs))
    assert out["turn_start_id"] == "new-q"


def test_intent_classify_write_keywords_writes_turn_start_id(monkeypatch):
    """WRITE_KEYWORDS 兜底:写 turn_start_id。"""
    monkeypatch.setattr(nodes.settings, "FORCE_INTENT", "")
    msgs = [HumanMessage(content="本轮问题", id="kw-q")]
    out = intent_classify(_state(question="请保存为笔记", messages=msgs))
    assert out["intent"] == "note_write"
    assert out["turn_start_id"] == "kw-q"


def test_intent_classify_normal_classify_writes_turn_start_id(monkeypatch):
    """正常分类路径:写 turn_start_id。"""
    class _FakeResp:
        intent = "knowledge"
        reason = "知识库"
        task_brief = ""

    class _FakeStructured:
        def invoke(self, msgs):
            return _FakeResp()

    class _FakeProvider:
        def with_structured_output(self, model):
            return _FakeStructured()

    monkeypatch.setattr(nodes.settings, "FORCE_INTENT", "")
    monkeypatch.setattr(nodes, "get_deepseek_provider", lambda: _FakeProvider())
    msgs = [HumanMessage(content="本轮问题", id="cls-q")]
    out = intent_classify(_state(question="本轮问题", messages=msgs))
    assert out["intent"] == "knowledge"
    assert out["turn_start_id"] == "cls-q"


# ---------- 层2:多轮图级回归(真实 SqliteSaver) ----------

def _build_regression_graph(checkpointer):
    g = StateGraph(AgentState)
    g.add_node("intent_classify", intent_classify)
    g.add_node("agent_step", agent_step)
    g.add_node("output", output)
    g.add_edge(START, "intent_classify")
    g.add_edge("intent_classify", "agent_step")
    g.add_edge("agent_step", "output")
    g.add_edge("output", END)
    return g.compile(checkpointer=checkpointer)


def test_multi_turn_answers_match_expected_with_sqlite_saver(monkeypatch):
    """30 轮纯问答:每轮答案 == 本轮期望。真实 SqliteSaver 临时文件,
    message id 序列化后仍可定位(裁剪后不越界)。"""
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
        graph = _build_regression_graph(saver)
        config = {"configurable": {"thread_id": "turn-regression"}}
        turns = [(f"第{i}轮问题", f"第{i}轮答案") for i in range(30)]
        for q, expected in turns:
            answer_holder["value"] = expected
            result = list(graph.stream(build_input(q, "turn-regression", "u1"), config=config))
            answer = result[-1]["output"]["answer"]
            assert answer == expected, f"第{q}轮答案应为 {expected!r},实得 {answer!r}"
    finally:
        conn.close()
        os.unlink(path)
