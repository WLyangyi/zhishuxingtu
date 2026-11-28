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
from langchain_core.messages import AIMessage, HumanMessage
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


def test_web_research_prompt_forbids_invented_citation_numbers():
    """引用只能来自编号来源列表，模型不得自编编号或无证据补写。"""
    from app.services.agent.prompts import WEB_RESEARCH_AGENT_PROMPT as P

    assert "只能使用编号来源列表中的 [n]" in P
    assert "不得自编编号" in P
    assert "没有证据时不得补写" in P


def test_web_research_prompt_covers_complete_usage_question():
    """w02 回归：官方用法问题需覆盖异步与同步边界，并允许换关键词补抓官方页面。"""
    from app.services.agent.prompts import WEB_RESEARCH_AGENT_PROMPT as P

    assert "问题的每个部分" in P
    assert "不要只抓一个页面就收尾" in P
    assert "换关键词" in P and "官方" in P
    assert "逐项回答" in P
    assert "同步驱动" in P and "async def" in P and "阻塞" in P


def test_web_research_prompt_limits_claims_to_retrieved_major_points():
    """w01 回归：主要特性题应简洁作答，且不得补写工具证据之外的细节。"""
    from app.services.agent.prompts import WEB_RESEARCH_AGENT_PROMPT as P

    assert "主要特性" in P and "控制篇幅" in P
    assert "未在工具结果中出现" in P and "不要补写" in P


def test_web_research_prompt_bounds_major_feature_answer():
    """w01 回归：主要特性列表必须有数量上限，并省略代码示例和边缘细节。"""
    from app.services.agent.prompts import WEB_RESEARCH_AGENT_PROMPT as P

    assert "最多 6 条" in P
    assert "省略代码示例" in P and "边缘细节" in P


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


def test_execute_tool_web_search_stamps_retrieval_time(monkeypatch):
    """联网摘要进入证据池时携带 UTC 检索时间，来源卡片无需借用网页发布日期。"""
    from datetime import datetime

    class FakeSearch:
        name = "web_search"

        def invoke(self, args):
            return json.dumps(
                [{"title": "T", "url": "https://e.com", "snippet": "摘要"}],
                ensure_ascii=False,
            )

    out = _run_tool_once(monkeypatch, "web_search", FakeSearch(), {"query": "q"}, thread="ws-time")

    retrieved_at = datetime.fromisoformat(out["documents"][0]["retrieved_at"])
    assert retrieved_at.utcoffset().total_seconds() == 0


def test_execute_tool_web_fetch_error_not_collected(monkeypatch):
    """行为24：web_fetch error dict 不入 documents（失败结果不是证据）。"""
    class FakeFetchErr:
        name = "web_fetch"

        def invoke(self, args):
            return json.dumps({"error": "web_fetch 无可用正文(404),请换源", "url": args["url"]}, ensure_ascii=False)

    out = _run_tool_once(monkeypatch, "web_fetch", FakeFetchErr(), {"url": "https://e.com/p"}, thread="fetch-err")
    assert out["documents"] == []


def test_execute_tool_web_fetch_failure_marks_existing_summary(monkeypatch):
    """抓取失败保留搜索摘要，并让来源聚合能区分失败与未抓取。"""
    class FakeFetchErr:
        name = "web_fetch"

        def invoke(self, args):
            return json.dumps({"error": "404", "url": args["url"]}, ensure_ascii=False)

    monkeypatch.setitem(execute_tool.__globals__["TOOL_MAP"], "web_fetch", FakeFetchErr())
    out = execute_tool({
        "messages": [AIMessage(content="", tool_calls=[
            {"name": "web_fetch", "args": {"url": "https://e.com/p"}, "id": "c1", "type": "tool_call"}
        ])],
        "documents": [{"title": "搜索页", "url": "https://e.com/p", "snippet": "摘要"}],
        "thoughts": [],
        "tool_calls_log": [],
    })

    assert len(out["documents"]) == 1
    assert out["documents"][0]["snippet"] == "摘要"
    assert out["documents"][0]["fetch_failed"] is True


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


def test_web_research_prompt_injects_stable_numbered_sources(monkeypatch):
    """多次检索后，模型每轮看到的编号来源与证据首次出现顺序一致。"""
    captured = []

    class FakeResponse:
        content = "整理中"
        tool_calls = []
        usage_metadata = {"total_tokens": 10}

    class FakeModel:
        def invoke(self, messages):
            captured.append(messages)
            return FakeResponse()

    class FakeProvider:
        def bind_tools(self, *args, **kwargs):
            return FakeModel()

        def get_chat_model(self):
            return FakeModel()

    monkeypatch.setitem(nodes.agent_step.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    first_doc = {"title": "第一页", "url": "https://example.com/a", "snippet": "摘要 A"}
    second_doc = {"title": "第二页", "url": "https://example.com/b", "snippet": "摘要 B"}
    base = {
        "question": "问题",
        "current_agent": "web_search",
        "intent": "web_search",
        "messages": [HumanMessage(content="问题")],
        "documents": [first_doc],
        "thoughts": [],
        "tool_calls_log": [],
        "user_id": "",
        "session_id": "sources-prompt",
    }

    nodes.agent_step({**base, "iteration": 0, "token_used": 0})
    nodes.agent_step({
        **base,
        "iteration": 1,
        "token_used": 10,
        "documents": [first_doc, second_doc],
    })

    prompt = "\n".join(str(message.content) for message in captured[-1])
    assert "[1] 第一页 https://example.com/a" in prompt
    assert "[2] 第二页 https://example.com/b" in prompt
    assert prompt.index("[1] 第一页") < prompt.index("[2] 第二页")


def test_web_research_last_iteration_synthesizes_from_fetched_evidence(monkeypatch):
    """达到迭代上限时，联网助手必须用已抓正文收尾，不能再发起工具调用或只回标题列表。"""
    from langchain_core.messages import HumanMessage

    captured = {}

    class FakeResponse:
        content = "WAL 通过独立日志允许读写并发，并由 checkpoint 合并回主库。"
        tool_calls = []
        usage_metadata = {"total_tokens": 321}

    class FakeModel:
        def invoke(self, messages):
            captured["messages"] = messages
            return FakeResponse()

    class FakeProvider:
        def bind_tools(self, *args, **kwargs):
            raise AssertionError("收尾轮不应再绑定工具")

        def get_chat_model(self):
            return FakeModel()

    monkeypatch.setitem(nodes.agent_step.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    search_docs = [
        {"title": f"摘要{i}", "url": f"https://example.com/{i}", "snippet": "摘要" * 300}
        for i in range(6)
    ]
    fetched = {
        "title": "Write-Ahead Logging",
        "url": "https://www.sqlite.org/wal.html",
        "snippet": "WAL allows readers and a writer to coexist.",
        "full_content": "开头" * 700 + "WAL allows readers and a writer to coexist; checkpoint merges the wal file.",
    }
    out = nodes.agent_step({
        "question": "SQLite 官方文档中 WAL 模式的作用是什么？",
        "current_agent": "web_search",
        "intent": "web_search",
        "iteration": nodes.MAX_ITERATIONS - 1,
        "token_used": 1000,
        "messages": [HumanMessage(content="SQLite WAL")],
        "documents": [*search_docs, fetched],
        "thoughts": [],
        "tool_calls_log": [],
        "user_id": "",
        "session_id": "synthesis",
    })

    assert out["iteration"] == nodes.MAX_ITERATIONS
    assert out["messages"][-1].content == FakeResponse.content
    evidence = captured["messages"][-1].content
    assert fetched["url"] in evidence
    assert "checkpoint merges the wal file" in evidence


def test_hallucination_check_prioritizes_fetched_full_content(monkeypatch):
    """搜索摘要很多时，幻觉查必须先核对已抓正文，不能因前五条摘要挤掉正文依据。"""
    captured = {}
    monkeypatch.setitem(
        nodes.hallucination_check.__globals__,
        "get_deepseek_provider",
        _fake_grade_provider(captured),
    )
    monkeypatch.setattr(nodes.settings, "USE_THREE_CHECK", True)
    docs = [
        {"title": f"摘要{i}", "url": f"https://example.com/{i}",
         "snippet": f"SEARCH_ONLY_{i}" + "摘要" * 300}
        for i in range(6)
    ]
    docs.append({
        "title": "官方正文",
        "url": "https://docs.python.org/3.12/whatsnew.html",
        "snippet": "开头",
        "full_content": "正文" * 750 + "FETCHED_EVIDENCE_MARKER",
    })

    out = nodes.hallucination_check({"answer": "答案", "documents": docs, "thoughts": []})

    assert out["hallucination_ok"] == "yes"
    evidence = captured["msgs"][1].content
    assert "FETCHED_EVIDENCE_MARKER" in evidence
    assert "SEARCH_ONLY_5" not in evidence
