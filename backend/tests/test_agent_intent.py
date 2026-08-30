# -*- coding: utf-8 -*-
import json

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.services.agent.nodes import (
    agent_step,
    direct_answer,
    execute_tool,
    generate,
    intent_classify,
    route_intent,
    route_intent_multi,
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


def test_intent_classify_sets_current_agent_and_turn_start(monkeypatch):
    """M7 A′:intent_classify 需写入 current_agent 与 turn_start_index(本轮起点)。"""
    from langchain_core.messages import HumanMessage

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
    msgs = [AIMessage(content="上一轮的旧答案"), HumanMessage(content="今天有什么AI新闻")]
    out = intent_classify(_state(question="今天有什么AI新闻", messages=msgs))
    assert out["intent"] == "web_search"
    assert out["current_agent"] == "web_search"
    assert out["turn_start_index"] == 1  # 最后一条(本轮新问题)在通道中的下标
    assert out["task_brief"] == ""  # 模型未返回 task_brief 时为空(为空不注入)


def test_intent_classify_writes_task_brief(monkeypatch):
    """M7.1:分类器返回的任务简报要写入 state,为空/缺失时不编造。"""
    class FakeResp:
        intent = "knowledge"
        reason = "知识库内容"
        task_brief = "查询克劳德code安装的前置条件"

    class FakeStructured:
        def invoke(self, msgs):
            return FakeResp()

    class FakeProvider:
        def with_structured_output(self, model):
            return FakeStructured()

    monkeypatch.setitem(intent_classify.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    out = intent_classify(_state(question="安装克劳德code之前需要先安装什么？"))
    assert out["task_brief"] == "查询克劳德code安装的前置条件"

    class FakeRespNoBrief:
        intent = "knowledge"
        reason = "知识库内容"

    class FakeStructuredNoBrief:
        def invoke(self, msgs):
            return FakeRespNoBrief()

    class FakeProviderNoBrief:
        def with_structured_output(self, model):
            return FakeStructuredNoBrief()

    monkeypatch.setitem(
        intent_classify.__globals__, "get_deepseek_provider", lambda: FakeProviderNoBrief()
    )
    out2 = intent_classify(_state(question="测试"))
    assert out2["task_brief"] == ""


def test_agent_step_injects_task_brief_first_round_only(monkeypatch):
    """M7.1:任务简报首轮注入 system prompt(为空不注入),次轮不重复注入(同意图提示的防死循环逻辑)。"""
    from langchain_core.messages import HumanMessage

    captured = {}

    class FakeLLM:
        def invoke(self, msgs):
            captured["system"] = msgs[0].content
            return AIMessage(content="ok")

    class FakeProvider:
        def bind_tools(self, tools):
            return FakeLLM()

    monkeypatch.setitem(agent_step.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    monkeypatch.setitem(agent_step.__globals__, "get_preference_context", lambda *a, **k: "")

    base = {
        "messages": [HumanMessage(content="问题")],
        "thoughts": [],
        "current_agent": "knowledge",
        "intent": "knowledge",
    }
    agent_step({**base, "iteration": 0, "task_brief": "查询克劳德code安装的前置条件"})
    assert "编排器任务简报" in captured["system"]
    assert "克劳德code" in captured["system"]

    agent_step({**base, "iteration": 0, "task_brief": ""})
    assert "编排器任务简报" not in captured["system"]  # 为空不注入

    agent_step({**base, "iteration": 1, "task_brief": "查询克劳德code安装的前置条件"})
    assert "编排器任务简报" not in captured["system"]  # 次轮不重复注入


def test_best_answer_scoped_to_current_turn():
    """M7.0 跨轮污染修复:上一轮长答案不得盖掉本轮短答案;
    不带 turn_start_index 时保持旧行为(全通道取最长)。"""
    from langchain_core.messages import HumanMessage

    msgs = [
        HumanMessage(content="旧问题"),
        AIMessage(content="这是一轮非常非常长的旧答案,长度远超本轮答案,若不限定本轮范围会被误选为答案。"),
        HumanMessage(content="新问题"),
        AIMessage(content="短答案"),
    ]
    # 旧行为(无 turn_start_index):全通道取最长
    assert "非常非常长" in generate({"messages": msgs})["answer"]
    # 新行为(M7.0):只在本轮范围内取
    out = generate({"messages": msgs, "turn_start_index": 2})
    assert out["answer"] == "短答案"


def test_route_intent_multi_maps_intent_to_agent_names():
    """M7 A′ 多 Agent 路由:意图 → agent 名,未知意图 fail-safe 回 knowledge_agent。"""
    assert route_intent_multi({"intent": "direct_answer"}) == "chat_agent"
    assert route_intent_multi({"intent": "knowledge"}) == "knowledge_agent"
    assert route_intent_multi({"intent": "web_search"}) == "web_research_agent"
    assert route_intent_multi({"intent": "note_write"}) == "note_write_agent"
    assert route_intent_multi({}) == "knowledge_agent"


def test_multi_agent_graph_compiles_and_routes():
    """A′ 多 Agent 图可编译,路由语义:chat→direct_answer,其余→agent_step。"""
    from app.services.agent.graph import build_multi_agent_graph

    graph = build_multi_agent_graph().compile()
    node_names = set(graph.get_graph().nodes)
    assert {"intent_classify", "direct_answer", "agent_step", "output"} <= node_names


def test_agent_configs_knowledge_specialized():
    """M7.2:knowledge_agent 工具集移出 create_note(HITL 专职 note_write),
    web_search 保留作回退(拍板),专属 prompt 声明职责边界;
    note_write 配置保留写入能力(M7.3 前由现配置承载)。"""
    from app.services.agent.nodes import AGENT_CONFIGS

    k_tools = {t.name for t in AGENT_CONFIGS["knowledge"]["tools"]}
    assert "create_note" not in k_tools
    assert "web_search" in k_tools  # 拍板:保留回退
    assert k_tools == {"search_notes", "get_note", "get_graph_neighbors", "list_tags", "list_folders", "web_search"}
    assert "职责边界" in AGENT_CONFIGS["knowledge"]["system_prompt"]
    assert "不执行任何写入操作" in AGENT_CONFIGS["knowledge"]["system_prompt"]
    assert "create_note" in {t.name for t in AGENT_CONFIGS["note_write"]["tools"]}


def test_agent_configs_specialists_m73():
    """M7.3:web_research/note_write 专职化——工具面收窄,提示词职责明确。"""
    from app.services.agent.nodes import AGENT_CONFIGS

    w_tools = {t.name for t in AGENT_CONFIGS["web_search"]["tools"]}
    n_tools = {t.name for t in AGENT_CONFIGS["note_write"]["tools"]}
    assert w_tools == {"web_search", "search_notes"}
    assert n_tools == {"create_note", "search_notes"}
    # web_research:信源引用要求
    assert "来源" in AGENT_CONFIGS["web_search"]["system_prompt"]
    # note_write:查重流程 + 审批提示
    assert "search_notes" in AGENT_CONFIGS["note_write"]["system_prompt"]
    assert "审批" in AGENT_CONFIGS["note_write"]["system_prompt"]


def test_three_check_routing_by_agent():
    """M7.3:三查按 current_agent 分叉——web_research 跳文档评级且无 answer_quality;
    note_write 无三查;knowledge 行为不变。"""
    from langchain_core.messages import AIMessage

    from app.services.agent.nodes import (
        route_grade_documents,
        route_hallucination,
        should_continue,
    )

    # web_search:should_continue 直接分流到 generate,绕过 grade_documents 节点
    # (route_grade_documents 是节点之后的条件边,在那里"跳过"为时已晚——M7.3 实测踩坑)
    msgs = [AIMessage(content="done")]
    assert should_continue({"messages": msgs, "current_agent": "web_search", "iteration": 1}) == "generate"
    assert route_grade_documents({"current_agent": "web_search", "documents_grade": "no"}) == "rewrite_question"  # 防御兜底
    # knowledge:行为不变
    assert should_continue({"messages": msgs, "current_agent": "knowledge", "iteration": 1}) == "grade_documents"
    assert route_grade_documents({"documents_grade": "no"}) == "rewrite_question"
    assert route_grade_documents({"documents_grade": "yes"}) == "generate"

    # web_search:幻觉查通过直接 output,不进 answer_quality(明示取舍)
    assert route_hallucination({"current_agent": "web_search", "hallucination_ok": "yes"}) == "output"
    assert route_hallucination({"current_agent": "web_search", "hallucination_ok": "no"}) == "rewrite_question"
    # knowledge:幻觉查通过仍进 answer_quality
    assert route_hallucination({"hallucination_ok": "yes"}) == "answer_quality"

    # note_write:ReAct 结束直接 output(无三查,人工审批即质量关)
    assert should_continue({"messages": msgs, "current_agent": "note_write", "iteration": 1}) == "output"


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
