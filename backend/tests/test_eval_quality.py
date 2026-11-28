# -*- coding: utf-8 -*-
"""联网评估证据与数据集绑定回归。"""
from eval import run_eval


def test_agent_full_sources_prioritizes_fetched_full_content():
    """w01 回归：裁判证据先放已抓正文，避免被前几条搜索摘要挤出 12000 字窗口。"""
    sources = [
        {"title": f"摘要{i}", "url": f"https://example.com/{i}", "snippet": "摘要" * 900}
        for i in range(8)
    ]
    sources.append({
        "title": "官方正文",
        "url": "https://docs.python.org/3.12/whatsnew.html",
        "snippet": "开头",
        "full_content": "正文" * 1500 + "OFFICIAL_FULL_CONTENT_MARKER",
    })

    full = run_eval.agent_full_sources([], sources, db=None)

    assert full[0]["title"] == "官方正文"
    assert "OFFICIAL_FULL_CONTENT_MARKER" in full[0]["content"]


def test_agent_full_sources_prioritizes_fetched_over_local_notes():
    """混合检索回归：已抓联网正文先于本地笔记，避免被多条本地全文挤出裁判窗口。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base import Base
    from app.models.note import Note

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        db.add(Note(id="n1", title="本地笔记", content="LOCAL_NOTE_CONTENT"))
        db.commit()
        sources = [
            {"title": f"摘要{i}", "url": f"https://example.com/{i}", "snippet": "摘要" * 900}
            for i in range(5)
        ]
        sources.append({
            "title": "官方正文",
            "url": "https://docs.python.org/3.12/whatsnew.html",
            "snippet": "开头",
            "full_content": "正文" * 1500 + "OFFICIAL_FULL_CONTENT_MARKER",
        })

        full = run_eval.agent_full_sources(["n1"], sources, db)

        assert full[0]["title"] == "官方正文"
        assert "OFFICIAL_FULL_CONTENT_MARKER" in full[0]["content"]
        assert any(item.get("id") == "n1" for item in full)
    finally:
        db.close()
        engine.dispose()


def test_faithfulness_retries_with_compact_schema_after_timeout(monkeypatch):
    """w03 回归：详细 claims 评分超时后，用同一证据做紧凑评分，不再原样重试导致空分。"""
    from types import SimpleNamespace
    from app.services.llm import judge_metrics

    captured = {}

    class Detailed:
        def invoke(self, prompt):
            captured["detailed"] = prompt
            raise TimeoutError("Request timed out")

    class Compact:
        def invoke(self, prompt):
            captured["compact"] = prompt
            return SimpleNamespace(score=0.88, reason="关键声明均有依据")

    class Provider:
        def with_structured_output(self, model, **kwargs):
            if model is judge_metrics.FaithfulnessGrade:
                return Detailed()
            if model is judge_metrics.FaithfulnessSummary:
                return Compact()
            raise AssertionError(f"unexpected schema: {model}")

    monkeypatch.setitem(judge_metrics.judge_faithfulness.__globals__, "get_judge_provider", lambda: Provider())

    out = judge_metrics.judge_faithfulness(
        "HTTP 429 是什么？",
        "429 表示请求过多，可根据 Retry-After 退避重试。",
        [{"title": "RFC 6585", "content": "429 means too many requests; Retry-After may be included."}],
    )

    assert out["score"] == 0.88
    assert out["degraded"] is True
    assert "Retry-After" in captured["compact"]
    assert "只输出总体分数" in captured["compact"]
    assert '"claims"' not in captured["compact"]


def test_agent_recall_counts_docs_from_later_searches():
    """Agent 多次检索的累计证据都应参与召回，不能只取证据池前 5 篇。"""
    retrieved = [f"noise-{i}" for i in range(5)] + ["think-a", "think-b"]

    assert run_eval.agent_recall(retrieved, ["doubao", "think-a", "think-b"]) == 2 / 3


def test_q039_accepts_duplicate_cloud_code_note_as_relevant():
    """q039 回归：同一视频的重复导入笔记也应参与相关性判定，不能误报检索遗漏。"""
    import json
    from pathlib import Path

    eval_dir = Path(run_eval.__file__).parent
    main_set = json.loads((eval_dir / "eval_set_v1.json").read_text(encoding="utf-8"))
    similar_set = json.loads(
        (eval_dir / "eval_set_similar_docs.json").read_text(encoding="utf-8")
    )
    q039 = next(item for item in main_set if item["id"] == "q039")
    s02 = next(item for item in similar_set if item["id"] == "s02")

    assert set(s02["relevant_doc_ids"]) <= set(q039["relevant_doc_ids"])
    retrieved = ["ab11270b-d216-4f3a-bfb8-65c26cc319f9", s02["relevant_doc_ids"][1]]
    assert run_eval.agent_recall(retrieved, q039["relevant_doc_ids"]) == 2 / 3


def test_run_agent_merges_fetched_body_for_same_url(monkeypatch):
    """w01 回归：同 URL 先出现搜索摘要、后出现 Fetch 正文时，eval 必须保留正文而非丢弃。"""
    from types import SimpleNamespace
    from app.services.agent import graph as agent_graph
    from app.services.observability import langfuse_trace
    from app.services.tools import context as tool_context

    summary = {
        "title": "Python 3.12 有什么新变化",
        "url": "https://docs.python.org/zh-cn/3.14/whatsnew/3.12.html",
        "snippet": "搜索摘要",
        "rerank_score": 2.0,
    }
    fetched = {
        "title": "Python 3.12 有什么新变化",
        "url": summary["url"],
        "snippet": "正文摘要",
        "full_content": "FETCHED_BODY_MARKER",
    }

    class FakeGraph:
        def stream(self, input_data, config):
            yield {"search": {"documents": [summary]}}
            yield {"fetch": {"documents": [summary, fetched], "tool_calls_log": [{"tool": "web_fetch"}]}}
            yield {"output": {"answer": "最终答案", "documents": [summary, fetched]}}

        def get_state(self, config):
            return SimpleNamespace(values={"intent": "web_search", "token_used": 123})

    monkeypatch.setattr(agent_graph, "build_input", lambda *args, **kwargs: {"question": "q"})
    monkeypatch.setattr(agent_graph, "get_graph", lambda: FakeGraph())
    monkeypatch.setattr(langfuse_trace, "build_stream_config", lambda thread_id: {})
    monkeypatch.setattr(tool_context, "set_tool_context", lambda ctx: None)

    _, answer, documents, intent, tool_calls, _, token_used = run_eval.run_agent("q", "u1")

    assert answer == "最终答案"
    assert intent == "web_search"
    assert tool_calls == 1
    assert token_used == 123
    assert len(documents) == 1
    assert documents[0]["full_content"] == "FETCHED_BODY_MARKER"
    assert documents[0]["rerank_score"] == 2.0
