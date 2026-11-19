# -*- coding: utf-8 -*-
"""回归用例:save-as-note(note_write)写入链路修复(交接文档 cbbccc5 + 9275b34)。

覆盖三层地基:
1. provider.bind_tools 必须透传 tool_choice(否则 9275b34 的 required 强制在入口就 TypeError);
2. agent_step 对 note_write 未写入时用 tool_choice=required、写入后回落 auto,并在模型
   无 tool_calls 时注入强制反馈重试;
3. should_continue 让 note_write 的工具结果回 agent_step(查重后能继续走到 create_note),
   模型文字收尾时才 output,且有 MAX_ITERATIONS 硬上限防死循环。
另含关键词兜底与意图读写边界。
"""
import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from app.services.agent import nodes as nodes_mod
from app.services.agent.nodes import agent_step, intent_classify, output, should_continue
from app.services.agent.config import TOKEN_BUDGET


# ---------- 1. provider 透传 tool_choice ----------
def test_deepseek_provider_bind_tools_forwards_tool_choice():
    """核心回归:DeepSeekProvider.bind_tools 必须接受并透传 tool_choice。

    交接文档 9275b34 调用 provider.bind_tools(tools, tool_choice="required"),
    旧签名只有 def bind_tools(self, tools) -> 直接 TypeError,写入链路从未跑通。
    """
    from app.services.llm.deepseek_provider import DeepSeekProvider

    captured = {}

    class FakeLLM:
        def bind_tools(self, tools, **kwargs):
            captured["kwargs"] = kwargs
            return "bound"

    p = DeepSeekProvider.__new__(DeepSeekProvider)  # 跳过 __init__,不建真实 client
    p._llm = FakeLLM()

    out = p.bind_tools([], tool_choice="required")
    assert out == "bound"
    assert captured["kwargs"].get("tool_choice") == "required"

    # 不传时保持向后兼容(旧调用点 bind_tools(tools) 不能坏)
    out2 = p.bind_tools([])
    assert out2 == "bound"
    assert "tool_choice" not in captured["kwargs"]


# ---------- 2. agent_step 强制工具 ----------
def _patch_agent_step(monkeypatch, responses):
    """替换 provider;bind_tools 记录 tool_choice;invoke 按 responses 顺序返回。"""
    state_seen = {"tool_choice": [], "invoke_calls": 0}

    class FakeLLM:
        def invoke(self, msgs):
            idx = state_seen["invoke_calls"]
            state_seen["invoke_calls"] += 1
            return responses[min(idx, len(responses) - 1)]

    class FakeProvider:
        def bind_tools(self, tools, tool_choice=None):
            state_seen["tool_choice"].append(tool_choice)
            return FakeLLM()

    monkeypatch.setitem(agent_step.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    monkeypatch.setitem(agent_step.__globals__, "get_preference_context", lambda *a, **k: "")
    return state_seen


def test_agent_step_note_write_uses_required_before_create(monkeypatch):
    """未调过 create_note 时,首轮必须用 tool_choice=required 强制模型出工具。"""
    seen = _patch_agent_step(monkeypatch, [AIMessage(content="")])
    base = {
        "messages": [AIMessage(content="用户想保存")],
        "current_agent": "note_write",
        "intent": "note_write",
        "iteration": 0,
        "tool_calls_log": [],
        "thoughts": [],
    }
    agent_step(base)
    assert seen["tool_choice"][0] == "required"


def test_agent_step_note_write_falls_back_to_auto_after_create(monkeypatch):
    """create_note 已在 tool_log(审批完成/被拒)后回落 auto,让模型能文字收尾。"""
    seen = _patch_agent_step(monkeypatch, [AIMessage(content="已保存")])
    base = {
        "messages": [AIMessage(content="用户想保存")],
        "current_agent": "note_write",
        "intent": "note_write",
        "iteration": 1,
        "tool_calls_log": [{"tool": "create_note", "status": "success"}],
        "thoughts": [],
    }
    agent_step(base)
    assert seen["tool_choice"][0] is None


def test_agent_step_forces_retry_when_no_tool_calls(monkeypatch):
    """模型在 note_write 下直接文字复述(无 tool_calls)时,注入强制反馈再调一次。"""
    forced_call = AIMessage(
        content="",
        tool_calls=[
            {"name": "search_notes", "args": {"query": "标题"}, "id": "c1", "type": "tool_call"}
        ],
    )
    seen = _patch_agent_step(monkeypatch, [AIMessage(content="复述了一堆内容"), forced_call])
    base = {
        "messages": [AIMessage(content="把总结存为笔记")],
        "current_agent": "note_write",
        "intent": "note_write",
        "iteration": 0,
        "tool_calls_log": [],
        "thoughts": [],
    }
    out = agent_step(base)
    assert seen["invoke_calls"] == 2  # 触发了强制重试
    # 最终写入 state 的是第二次带 tool_calls 的响应
    assert out["messages"][-1].tool_calls[0]["name"] == "search_notes"


def test_agent_step_retry_stops_after_second_no_tool_call(monkeypatch):
    """第二次仍无 tool_calls 时放行(防死循环),不无限重试。"""
    seen = _patch_agent_step(
        monkeypatch, [AIMessage(content="复述一"), AIMessage(content="复述二")]
    )
    base = {
        "messages": [AIMessage(content="存为笔记")],
        "current_agent": "note_write",
        "intent": "note_write",
        "iteration": 0,
        "tool_calls_log": [],
        "thoughts": [],
    }
    agent_step(base)
    assert seen["invoke_calls"] == 2  # 恰好两次,不再多


def test_agent_step_non_note_write_never_forces(monkeypatch):
    """knowledge 等其它 agent 不受 required 强制(避免全局误伤)。"""
    seen = _patch_agent_step(monkeypatch, [AIMessage(content="ok")])
    base = {
        "messages": [AIMessage(content="问题")],
        "current_agent": "knowledge",
        "intent": "knowledge",
        "iteration": 0,
        "tool_calls_log": [],
        "thoughts": [],
    }
    agent_step(base)
    assert seen["tool_choice"][0] is None


# ---------- 3. should_continue 回环 ----------
def test_should_continue_note_write_toolmessage_loops_back():
    """note_write:工具结果(ToolMessage)必须回 agent_step,否则查重后走不到 create_note。"""
    last = ToolMessage(content="查重结果", tool_call_id="c1")
    out = should_continue(
        {"messages": [last], "current_agent": "note_write", "iteration": 1, "token_used": 10}
    )
    assert out == "agent_step"


def test_should_continue_note_write_text_outputs():
    """note_write:模型文字收尾(无 tool_calls)时直接 output。"""
    out = should_continue(
        {
            "messages": [AIMessage(content="已保存")],
            "current_agent": "note_write",
            "iteration": 2,
            "token_used": 10,
        }
    )
    assert out == "output"


def test_should_continue_note_write_respects_iteration_cap():
    """note_write 回环必须有迭代硬上限,防止查重→写入反复回环烧穿 token。"""
    last = ToolMessage(content="查重结果", tool_call_id="c1")
    out = should_continue(
        {"messages": [last], "current_agent": "note_write", "iteration": 99, "token_used": 10}
    )
    assert out == "output"  # MAX_ITERATIONS 触发,不再回 agent_step


# ---------- 4. 关键词兜底 ----------
def _intent_without_llm(question):
    """关键词兜底命中时不应调用 LLM;用一个会炸的 provider 证明短路。"""
    class ExplodingProvider:
        def with_structured_output(self, model):
            raise AssertionError("命中关键词兜底时不应调用 LLM 分类")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setitem(
        intent_classify.__globals__, "get_deepseek_provider", lambda: ExplodingProvider()
    )
    try:
        return intent_classify({"question": question, "thoughts": [], "messages": []})
    finally:
        monkeypatch.undo()


@pytest.mark.parametrize(
    "question",
    [
        "把总结内容保存为笔记",
        "这段整理成笔记",
        "把 A 和 B 合并成一篇",
        "保存到知识库",
        "记下来",
    ],
)
def test_write_keywords_force_note_write(question):
    out = _intent_without_llm(question)
    assert out["intent"] == "note_write"
    assert out["current_agent"] == "note_write"
    assert out["task_brief"]  # 兜底分支带明确任务简报


def test_pure_summary_does_not_hit_write_keyword():
    """'总结一下知识库'不含写入动作,不应被关键词兜底误伤(交给 LLM 分类归 knowledge)。"""
    class FakeResp:
        intent = "knowledge"
        reason = "只总结不写入"
        task_brief = ""

    class FakeStructured:
        def invoke(self, msgs):
            return FakeResp()

    class FakeProvider:
        def with_structured_output(self, model):
            return FakeStructured()

    mp = pytest.MonkeyPatch()
    mp.setitem(intent_classify.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    try:
        out = intent_classify({"question": "总结一下知识库的内容", "thoughts": [], "messages": []})
    finally:
        mp.undo()
    assert out["intent"] == "knowledge"


# ---------- 5. 端到端实测发现的残留 bug ----------
def test_output_does_not_reuse_stale_cross_turn_answer():
    """跨轮污染回归:state 里残留的上一轮 answer 不得当成本轮答案输出。

    实测复现:第二轮"保存为笔记"命中 create_note 后因 token 超限被 should_continue
    强制 output,output 用了 state["answer"](上一轮总结)→ 用户看到复述、笔记没落库。
    output 必须与 generate 一致,只用本轮 _best_answer(messages, turn_start_index)。
    """
    msgs = [
        AIMessage(content="上一轮的总结,很长很完整,绝不能作为本轮答案"),
        AIMessage(content="本轮问题"),
        AIMessage(content="本轮正确的简短答复"),
    ]
    out = output(
        {
            "answer": "上一轮的总结,很长很完整,绝不能作为本轮答案",
            "messages": msgs,
            "turn_start_index": 1,
        }
    )
    assert "本轮正确" in out["answer"]
    assert "上一轮的总结" not in out["answer"]


def test_output_falls_back_to_current_turn_when_state_answer_stale(monkeypatch):
    """state answer 为空/过期时,output 仅从本轮消息兜底,不回退到跨轮。"""
    msgs = [
        AIMessage(content="上一轮残留"),
        AIMessage(content="本轮答复"),
    ]
    out = output({"answer": "", "messages": msgs, "turn_start_index": 1})
    assert out["answer"] == "本轮答复"


def test_token_budget_covers_typical_multi_turn_tool_chain():
    """单轮 token 预算必须容纳典型的多轮工具链(实测 note_write 两轮约 21079)。

    AGENT_TOKEN_BUDGET=10000 会在模型已生成 create_note tool_call 后误杀写入,
    导致用户明确的保存诉求被静默丢弃。预算应高于实测峰值且仍远低于会话级 200000。
    """
    assert TOKEN_BUDGET >= 30000
