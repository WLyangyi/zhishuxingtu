# -*- coding: utf-8 -*-
"""web_research 编排层契约：证据口径 / 工具面 / 熔断 / fetch 证据收集。

只在系统边界 mock：LLM 经 get_deepseek_provider（fake structured.invoke 捕获 messages），
DB 经 SessionLocal→内存 sqlite。不 mock _doc_text/compress_result 等内部协作者，
一律经公开节点接口断言。
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services.agent import nodes
from app.services.agent.nodes import execute_tool
from app.services.agent.state import AgentState
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver


def _run_tool_once(monkeypatch, tool_name, fake, args, call_id="c1", thread="t", log=None):
    """单节点图驱动 execute_tool 一轮，返回该轮输出（复用 test_agent_intent 熔断测试模式）。"""
    monkeypatch.setitem(execute_tool.__globals__["TOOL_MAP"], tool_name, fake)
    inp = {
        "messages": [AIMessage(content="", tool_calls=[
            {"name": tool_name, "args": args, "id": call_id, "type": "tool_call"}])],
        "thoughts": [], "tool_calls_log": log or [], "documents": [],
    }
    builder = StateGraph(AgentState)
    builder.add_node("execute_tool", execute_tool)
    builder.add_edge(START, "execute_tool")
    builder.add_edge("execute_tool", END)
    graph = builder.compile(checkpointer=MemorySaver())
    out = list(graph.stream(inp, config={"configurable": {"thread_id": thread}}))
    return out[-1]["execute_tool"]


def _fake_grade_provider(captured, binary_score="yes", reason="ok"):
    class FakeResp:
        pass

    resp = FakeResp()
    resp.binary_score = binary_score
    resp.reason = reason

    class FakeStructured:
        def invoke(self, msgs):
            captured["msgs"] = msgs
            return resp

    class FakeProvider:
        def with_structured_output(self, model):
            return FakeStructured()

    return lambda: FakeProvider()


def test_hallucination_evidence_web_sees_beyond_200_note_still_200(monkeypatch):
    """行为14：幻觉查证据按文档形状分流——联网文档可见 >200（full_content 优先、2000cap），
    笔记仍截 200。否则模型凭完整 summary 作答却被 200 字证据误判幻觉→rewrite 死循环。"""
    captured = {}
    monkeypatch.setitem(
        nodes.hallucination_check.__globals__,
        "get_deepseek_provider",
        _fake_grade_provider(captured),
    )
    monkeypatch.setattr(nodes.settings, "USE_THREE_CHECK", True)

    docs = [
        {"url": "https://e.com/a", "title": "网页A", "snippet": "a" * 790 + "MARK500"},
        {"url": "https://e.com/b", "title": "网页B", "snippet": "短",
         "full_content": "b" * 1490 + "MARK1500" + "c" * 3000},
        {"id": "n1", "title": "笔记", "snippet": "d" * 200 + "MARK200"},
    ]
    out = nodes.hallucination_check({"answer": "答案", "documents": docs, "thoughts": []})

    assert out["hallucination_ok"] == "yes"
    evidence = captured["msgs"][1].content
    assert "MARK500" in evidence       # 联网 snippet >200 可见
    assert "MARK1500" in evidence      # full_content 优先，2000cap 内
    assert "MARK200" not in evidence   # 笔记仍截 200


def test_web_fetch_tool_surface_and_mcp_boundary():
    """行为22：web_fetch 进 web_research 工具面、不进 knowledge；TOOL_MAP 可解析；
    权限表显式 READ 但 mcp_exposed=False（agent-only，限爆炸半径）。"""
    from app.services.agent.nodes import AGENT_CONFIGS, KNOWLEDGE_TOOLS, TOOL_MAP
    from app.services.tools.permissions import (
        READ,
        policy_for,
        should_register_on_mcp,
        tool_annotations,
    )

    w_tools = {t.name for t in AGENT_CONFIGS["web_search"]["tools"]}
    assert w_tools == {"web_search", "web_fetch", "search_notes", "read_tool_artifact"}
    k_tools = {t.name for t in KNOWLEDGE_TOOLS}
    assert k_tools == {"search_notes", "get_note", "get_graph_neighbors", "list_tags",
                       "list_folders", "web_search", "read_tool_artifact"}
    assert "web_fetch" in TOOL_MAP
    assert policy_for("web_fetch").level == READ
    assert policy_for("web_fetch").mcp_exposed is False
    assert should_register_on_mcp("web_fetch", enable_write=True, has_write_user=True) is False
    assert tool_annotations("web_search")["openWorldHint"] is True


def test_web_research_prompt_guides_fetch():
    """行为23：提示词引导先搜选优再 web_fetch 抓正文、403/404 换源；保留永久未启用回退/信源/只读职责。"""
    from app.services.agent.prompts import WEB_RESEARCH_AGENT_PROMPT as P

    assert "web_fetch" in P
    assert "正文" in P
    assert "403" in P and "404" in P
    assert "换源" in P
    assert "永久未启用" in P
    assert "search_notes" in P
    assert "来源:网络" in P
    assert "不执行写入" in P
    # 控制抓取开销:同源镜像/语言版本只抓一份、摘要够用即止(防重复抓取推高 token 触预算截断)
    assert "同源" in P and "镜像" in P
    assert "摘要已足够" in P


def test_execute_tool_collects_web_fetch_evidence(monkeypatch):
    """行为24：web_fetch 成功 dict → documents 含 {title,url,snippet:content[:800],full_content}。"""
    class FakeFetch:
        name = "web_fetch"

        def invoke(self, args):
            return json.dumps(
                {"title": "页面", "url": args["url"], "content": "# 正文\n" + "正" * 2000},
                ensure_ascii=False,
            )

    out = _run_tool_once(monkeypatch, "web_fetch", FakeFetch(), {"url": "https://e.com/p"}, thread="fetch-ev")
    docs = out["documents"]
    assert len(docs) == 1
    assert docs[0]["url"] == "https://e.com/p"
    assert docs[0]["title"] == "页面"
    assert docs[0]["full_content"].startswith("# 正文")
    assert len(docs[0]["snippet"]) == 800


def test_execute_tool_web_fetch_error_not_collected(monkeypatch):
    """行为24：web_fetch error dict 不入 documents（失败结果不是证据）。"""
    class FakeFetchErr:
        name = "web_fetch"

        def invoke(self, args):
            return json.dumps({"error": "web_fetch 无可用正文(404),请换源", "url": args["url"]}, ensure_ascii=False)

    out = _run_tool_once(monkeypatch, "web_fetch", FakeFetchErr(), {"url": "https://e.com/p"}, thread="fetch-err")
    assert out["documents"] == []


def test_execute_tool_web_search_extended_fields_collected(monkeypatch):
    """行为24：web_search 含扩展字段的 list 项照常入 documents（不回归）。"""
    class FakeSearch:
        name = "web_search"

        def invoke(self, args):
            return json.dumps(
                [{"title": "T", "url": "https://e.com", "snippet": "s" * 700,
                  "rerank_score": 2.5, "authority": 3, "date": "2026-01-01", "site_name": "SN"}],
                ensure_ascii=False,
            )

    out = _run_tool_once(monkeypatch, "web_search", FakeSearch(), {"query": "q"}, thread="ws-ev")
    docs = out["documents"]
    assert len(docs) == 1
    assert docs[0]["url"] == "https://e.com"
    assert docs[0]["rerank_score"] == 2.5


def test_breaker_web_search_empty_key_permanent(monkeypatch):
    """行为25a：deepseek+空 key 真实 web_search，一轮「永久未启用」、二轮短路「已确认永久不可用」，
    短路文案 provider 中立（不含 TAVILY），全程不发请求。"""
    from app.core.config import settings
    from app.services.tools import web_tools

    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "")
    monkeypatch.setattr(settings, "WEB_SEARCH_PROVIDER", "deepseek")
    monkeypatch.setattr(web_tools, "_cache", {})
    monkeypatch.setattr(web_tools, "MIN_INTERVAL", 0.0)
    posts = []

    def _no_post(*a, **k):
        posts.append(1)
        raise AssertionError("空 key 不应发请求")

    monkeypatch.setattr(web_tools.httpx, "post", _no_post)
    real_ws = nodes.TOOL_MAP["web_search"]

    out1 = _run_tool_once(monkeypatch, "web_search", real_ws, {"query": "AI 新闻"}, call_id="c1", thread="perm")
    log1 = out1["tool_calls_log"]
    assert log1[-1]["status"] == "error"
    assert "永久未启用" in log1[-1]["result"]

    out2 = _run_tool_once(monkeypatch, "web_search", real_ws, {"query": "AI 新闻"}, call_id="c2", thread="perm", log=log1)
    log2 = out2["tool_calls_log"]
    assert "已确认永久不可用" in log2[-1]["result"]
    assert "TAVILY" not in log2[-1]["result"]
    assert posts == []


def test_breaker_web_search_402_generic_not_permanent(monkeypatch):
    """行为25b：恒 402 三轮，真实 post 恰 2 次、三轮「已熔断」，短路文案不含「永久不可用」
    （402 是可重试失败，不误触永久熔断）。"""
    import httpx
    from app.core.config import settings
    from app.services.tools import web_tools

    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "WEB_SEARCH_PROVIDER", "deepseek")
    monkeypatch.setattr(web_tools, "_cache", {})
    monkeypatch.setattr(web_tools, "MIN_INTERVAL", 0.0)
    posts = []

    def _post_402(url, **kwargs):
        posts.append(url)
        return httpx.Response(402, json={"error": {"message": "insufficient"}}, request=httpx.Request("POST", url))

    monkeypatch.setattr(web_tools.httpx, "post", _post_402)
    real_ws = nodes.TOOL_MAP["web_search"]

    out1 = _run_tool_once(monkeypatch, "web_search", real_ws, {"query": "q"}, call_id="c1", thread="b402")
    log1 = out1["tool_calls_log"]
    assert "402" in log1[-1]["result"] and "永久未启用" not in log1[-1]["result"]
    out2 = _run_tool_once(monkeypatch, "web_search", real_ws, {"query": "q"}, call_id="c2", thread="b402", log=log1)
    log2 = out2["tool_calls_log"]
    out3 = _run_tool_once(monkeypatch, "web_search", real_ws, {"query": "q"}, call_id="c3", thread="b402", log=log2)
    log3 = out3["tool_calls_log"]

    assert len(posts) == 2
    assert "已熔断" in log3[-1]["result"]
    assert "永久不可用" not in log3[-1]["result"]


def test_breaker_web_fetch_invalid_url_generic(monkeypatch):
    """行为25c：web_fetch 非法 url 两次失败后三次→通用熔断（fetch 无永久特判，换源即可）。"""
    real_wf = nodes.TOOL_MAP["web_fetch"]
    out1 = _run_tool_once(monkeypatch, "web_fetch", real_wf, {"url": "ftp://x"}, call_id="c1", thread="wf")
    log1 = out1["tool_calls_log"]
    assert "URL 非法" in log1[-1]["result"]
    out2 = _run_tool_once(monkeypatch, "web_fetch", real_wf, {"url": "ftp://x"}, call_id="c2", thread="wf", log=log1)
    log2 = out2["tool_calls_log"]
    out3 = _run_tool_once(monkeypatch, "web_fetch", real_wf, {"url": "ftp://x"}, call_id="c3", thread="wf", log=log2)
    log3 = out3["tool_calls_log"]
    assert "已熔断" in log3[-1]["result"]
    assert "web_fetch" in log3[-1]["result"]