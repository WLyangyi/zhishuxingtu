import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.agent.sources import build_web_sources, validate_web_sources
from app.services.agent import nodes
from langchain_core.messages import AIMessage, HumanMessage


def test_build_web_sources_assigns_stable_session_scoped_source_id():
    docs = [{"title": "页面", "url": "https://example.com/a", "snippet": "摘要"}]

    first = build_web_sources(docs, session_id="s1")[0]
    replay = build_web_sources(docs, session_id="s1")[0]
    other_session = build_web_sources(docs, session_id="s2")[0]
    other_url = build_web_sources(
        [{"title": "页面", "url": "https://example.com/b", "snippet": "摘要"}],
        session_id="s1",
    )[0]

    assert first["source_id"] == replay["source_id"]
    assert first["source_id"] != other_session["source_id"]
    assert first["source_id"] != other_url["source_id"]


def test_build_web_sources_dedupes_exact_url_in_first_seen_order():
    docs = [
        {"title": "第一页", "url": "https://example.com/a", "snippet": "摘要 A"},
        {"title": "第二页", "url": "https://example.com/b", "snippet": "摘要 B"},
        {"title": "第一页重复", "url": "https://example.com/a", "snippet": "重复摘要"},
    ]

    sources = build_web_sources(docs, session_id="s1")

    assert [source["url"] for source in sources] == [
        "https://example.com/a",
        "https://example.com/b",
    ]
    assert [source["ordinal"] for source in sources] == [1, 2]
    assert sources[0]["title"] == "第一页"


def test_build_web_sources_merges_summary_and_fetch_with_body_excerpt_priority():
    docs = [
        {"title": "搜索标题", "url": "https://example.com/a", "snippet": "搜索摘要"},
        {
            "title": "正文标题",
            "url": "https://example.com/a",
            "snippet": "正文开头",
            "full_content": "完整正文依据",
        },
    ]

    sources = build_web_sources(docs, session_id="s1")

    assert len(sources) == 1
    assert sources[0]["title"] == "正文标题"
    assert sources[0]["excerpt"] == "完整正文依据"


def test_build_web_sources_normalizes_url_before_deduplication():
    docs = [
        {"title": "页面", "url": "HTTPS://Example.COM/Path?q=One#first", "snippet": "摘要"},
        {"title": "重复", "url": "https://example.com/Path?q=One#second", "snippet": "重复"},
    ]

    sources = build_web_sources(docs, session_id="s1")

    assert len(sources) == 1
    assert sources[0]["url"] == "https://example.com/Path?q=One"


def test_build_web_sources_marks_summary_only_source():
    sources = build_web_sources(
        [{"title": "页面", "url": "https://example.com/a", "snippet": "搜索摘要"}],
        session_id="s1",
    )

    assert sources[0]["content_state"] == "summary"


def test_build_web_sources_marks_source_with_body_as_fetched():
    sources = build_web_sources(
        [{"title": "页面", "url": "https://example.com/a", "full_content": "正文"}],
        session_id="s1",
    )

    assert sources[0]["content_state"] == "fetched"


def test_build_web_sources_marks_fetch_failure_without_losing_summary():
    docs = [
        {"title": "搜索标题", "url": "https://example.com/a", "snippet": "搜索摘要"},
        {"url": "https://example.com/a", "fetch_failed": True, "error": "404"},
    ]

    sources = build_web_sources(docs, session_id="s1")

    assert len(sources) == 1
    assert sources[0]["content_state"] == "fetch_failed"
    assert sources[0]["excerpt"] == "搜索摘要"
    assert sources[0]["title"] == "搜索标题"


def test_build_web_sources_carries_snapshot_provenance():
    doc = {
        "title": "页面",
        "url": "https://example.com/a",
        "full_content": "正文",
        "artifact_id": "artifact-1",
        "fetched_at": "2026-11-28T10:00:00+00:00",
        "retrieved_at": "2026-11-28T09:59:00+00:00",
        "site_name": "Example",
        "truncated": True,
    }

    source = build_web_sources([doc], session_id="s1")[0]

    assert source["artifact_id"] == "artifact-1"
    assert source["fetched_at"] == "2026-11-28T10:00:00+00:00"
    assert source["retrieved_at"] == "2026-11-28T09:59:00+00:00"
    assert source["site_name"] == "Example"
    assert source["truncated"] is True


def test_build_web_sources_generates_bounded_single_line_excerpt():
    raw = "  开头\n" + "正文" * 1000 + "  尾部  "

    source = build_web_sources(
        [{"url": "https://example.com/a", "full_content": raw}],
        session_id="s1",
    )[0]

    assert source["excerpt"].startswith("开头 正文")
    assert "\n" not in source["excerpt"]
    assert len(source["excerpt"]) == 501
    assert source["excerpt"].endswith("…")


def test_build_web_sources_ignores_non_http_urls():
    docs = [
        {"title": "本地文档", "url": "/notes/1", "snippet": "本地内容"},
        {"title": "危险协议", "url": "javascript:alert(1)", "snippet": "不可信"},
        {"title": "有效网页", "url": "https://example.com/a", "snippet": "摘要"},
    ]

    sources = build_web_sources(docs, session_id="s1")

    assert [source["url"] for source in sources] == ["https://example.com/a"]


def test_validate_web_sources_rejects_unsafe_url():
    source = build_web_sources(
        [{"title": "页面", "url": "https://example.com/a", "snippet": "摘要"}],
        session_id="s1",
    )[0]
    source["url"] = "javascript:alert(1)"

    assert validate_web_sources([source]) == []


def test_output_binds_web_sources_to_selected_final_message():
    question = HumanMessage(content="问题", id="q1")
    selected = AIMessage(content="完整回答 [1]", id="a1")
    state = {
        "messages": [question, AIMessage(content="短回答", id="a0"), selected],
        "turn_start_id": "q1",
        "current_agent": "web_search",
        "session_id": "s1",
        "documents": [{"title": "页面", "url": "https://example.com/a", "snippet": "摘要"}],
    }

    out = nodes.output(state)

    assert out["answer"] == "完整回答 [1]"
    assert out["messages"][0].id == "a1"
    assert out["messages"][0].additional_kwargs["sources"] == build_web_sources(
        state["documents"], "s1"
    )
