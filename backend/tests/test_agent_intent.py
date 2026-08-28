# -*- coding: utf-8 -*-
import json

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.services.agent.nodes import (
    direct_answer,
    execute_tool,
    generate,
    intent_classify,
    route_intent,
)
from app.services.agent.state import AgentState


def _state(**kw):
    base = {"question": "测试", "intent": "", "thoughts": [], "user_id": "u1", "session_id": "s1"}
    base.update(kw)
    return base


def test_route_intent_direct_answer_goes_to_direct_answer():
    assert route_intent({"intent": "direct_answer"}) == "direct_answer"


def test_route_intent_others_go_to_agent_step():
    assert route_intent({}) == "agent_step"
    assert route_intent({"intent": "knowledge"}) == "agent_step"
    assert route_intent({"intent": "web_search"}) == "agent_step"
    assert route_intent({"intent": "note_write"}) == "agent_step"


def test_intent_classify_sets_intent(monkeypatch):
    class FakeResp:
        intent = "web_search"
        reason = "需要实时信息"

    class FakeStructured:
        def invoke(self, msgs):
            return FakeResp()

    class FakeProvider:
        def with_structured_output(self, model):
            return FakeStructured()

    monkeypatch.setitem(intent_classify.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    out = intent_classify(_state(question="今天有什么AI新闻"))
    assert out["intent"] == "web_search"
    assert out["thoughts"][0]["type"] == "intent"


def test_intent_classify_fails_safe_to_knowledge(monkeypatch):
    class FakeProvider:
        def with_structured_output(self, model):
            raise RuntimeError("llm down")

    monkeypatch.setitem(intent_classify.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    out = intent_classify(_state())
    assert out["intent"] == "knowledge"


def test_intent_classify_rejects_invalid_intent(monkeypatch):
    class FakeResp:
        intent = "hacker"
        reason = "bad"

    class FakeStructured:
        def invoke(self, msgs):
            return FakeResp()

    class FakeProvider:
        def with_structured_output(self, model):
            return FakeStructured()

    monkeypatch.setitem(intent_classify.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    out = intent_classify(_state())
    assert out["intent"] == "knowledge"


def test_direct_answer_returns_answer_and_writes_checkpoint(monkeypatch):
    class FakeResp:
        content = "你好!有什么可以帮你?"

    class FakeChat:
        def invoke(self, msgs):
            return FakeResp()

    class FakeProvider:
        def get_chat_model(self):
            return FakeChat()

    monkeypatch.setitem(direct_answer.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    monkeypatch.setitem(
        direct_answer.__globals__, "get_preference_context", lambda *a, **k: ""
    )
    out = direct_answer(_state(question="你好"))
    assert out["answer"] == "你好!有什么可以帮你?"
    assert out["messages"][0].content == "你好"
    assert out["messages"][1].content == "你好!有什么可以帮你?"


def test_web_search_circuit_breaker_blocks_after_permanent_unavailable(monkeypatch):
    """web_search 返回"永久未启用"后，同线程后续 web_search 请求应被短路，不再真调工具。"""
    calls = []

    class FakeWebSearch:
        def invoke(self, args):
            calls.append(args)
            return json.dumps({"error": "web_search 永久未启用(.env 缺少 TAVILY_API_KEY)"}, ensure_ascii=False)

    monkeypatch.setitem(execute_tool.__globals__["TOOL_MAP"], "web_search", FakeWebSearch())

    def _tool_input(call_id, log=None):
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "web_search", "args": {"query": "AI 新闻"}, "id": call_id, "type": "tool_call"}
                    ],
                )
            ],
            "thoughts": [],
            "tool_calls_log": log or [],
            "documents": [],
        }

    builder = StateGraph(AgentState)
    builder.add_node("execute_tool", execute_tool)
    builder.add_edge(START, "execute_tool")
    builder.add_edge("execute_tool", END)
    graph = builder.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "ws-block"}}

    # 第一次:真实调用,返回"永久未启用"
    first = list(graph.stream(_tool_input("c1"), config=config))
    assert len(calls) == 1
    log1 = first[-1]["execute_tool"]["tool_calls_log"]
    assert log1[-1]["status"] == "error"
    assert "永久未启用" in log1[-1]["result"]

    # 第二次:同线程再次请求 web_search,应被熔断(不新增真实调用)
    second = list(graph.stream(_tool_input("c2", log=log1), config=config))
    assert len(calls) == 1  # 真实调用仍是 1 次
    log2 = second[-1]["execute_tool"]["tool_calls_log"]
    assert "已确认永久不可用" in log2[-1]["result"]
    assert log2[-1]["status"] == "error"


def test_generate_picks_longest_answer():
    """rewrite 循环后最后一条可能是退化短句,应取内容最长的 AIMessage 作为答案。"""
    from langchain_core.messages import HumanMessage

    msgs = [
        HumanMessage(content="q"),
        AIMessage(content="好答案,内容足够长,覆盖了问题全部要点并给出依据和结论。"),
        AIMessage(content="以上回答基于知识库中的三篇笔记。"),  # 退化的尾部短句
        AIMessage(content="", tool_calls=[{"name": "search_notes", "args": {"query": "x"}, "id": "c", "type": "tool_call"}]),
    ]
    out = generate({"messages": msgs})
    assert "好答案" in out["answer"]
    assert "以上回答基于" not in out["answer"]


def test_search_notes_dedup_blocks_repeat_query(monkeypatch):
    """同一轮内重复相同的 search_notes 检索词应被短路,防多跳检索死循环。"""
    calls = []

    class FakeSearchNotes:
        def invoke(self, args):
            calls.append(args)
            return json.dumps([{"id": "n1", "title": "笔记1", "snippet": "内容"}], ensure_ascii=False)

    monkeypatch.setitem(execute_tool.__globals__["TOOL_MAP"], "search_notes", FakeSearchNotes())

    def _tool_input(call_id, searched=None):
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "search_notes", "args": {"query": "吴浩阳 项目"}, "id": call_id, "type": "tool_call"}
                    ],
                )
            ],
            "thoughts": [],
            "tool_calls_log": [],
            "documents": [],
            "searched_queries": searched or [],
        }

    builder = StateGraph(AgentState)
    builder.add_node("execute_tool", execute_tool)
    builder.add_edge(START, "execute_tool")
    builder.add_edge("execute_tool", END)
    graph = builder.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "search-dedup"}}

    first = list(graph.stream(_tool_input("c1"), config=config))
    assert len(calls) == 1
    searched = first[-1]["execute_tool"]["searched_queries"]
    assert "吴浩阳 项目" in searched

    second = list(graph.stream(_tool_input("c2", searched=searched), config=config))
    assert len(calls) == 1  # 重复检索被短路,不新增真实调用
    log2 = second[-1]["execute_tool"]["tool_calls_log"]
    assert "请勿重复检索" in log2[-1]["result"]
