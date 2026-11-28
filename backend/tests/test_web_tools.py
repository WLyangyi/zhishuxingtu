"""联网工具（web_search / web_fetch）契约测试。

TDD 纵向切片：只在 httpx.post 系统边界 mock，经公开接口 web_search.func / web_fetch.func
断言行为，不 mock 内部协作者。任何测试不得发真实网络请求。
"""
import json
import os
import sys

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.services.tools import web_tools


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """重置模块全局 + 隔离真实 key + 默认 provider，杜绝真实网络与缓存串味。"""
    monkeypatch.setattr(web_tools, "_cache", {})
    monkeypatch.setattr(web_tools, "_last_call_ts", 0.0)
    monkeypatch.setattr(web_tools, "MIN_INTERVAL", 0.0)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "")
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "")
    monkeypatch.setattr(settings, "WEB_SEARCH_PROVIDER", "deepseek")
    monkeypatch.setattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def _patch_post(monkeypatch, payload=None, status=200, timeout=False):
    """唯一 mock 点 = web_tools.httpx.post。返回真实 httpx.Response 值对象，
    raise_for_status()/.json() 走真实实现；timeout=True 时抛 httpx.TimeoutException。"""
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        if timeout:
            raise httpx.TimeoutException("timeout")
        return httpx.Response(status, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(web_tools.httpx, "post", fake_post)
    return calls


# ---------- 阶段 A：provider 开关 + DeepSeek 搜索主链路 ----------

def test_deepseek_happy_path(monkeypatch):
    """行为1（tracer bullet）：provider=deepseek 时调官方 Search API，snippet 取 summary。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    payload = {"results": [{
        "rerank_score": 2.5, "authority": 3, "title": "T", "url": "https://e.com",
        "summary": "S" * 800, "snippet": "短", "site_name": "SN",
        "date": "2026-01-01T00:00:00+00:00",
    }]}
    calls = _patch_post(monkeypatch, payload=payload)

    out = json.loads(web_tools.web_search.func("q"))

    assert isinstance(out, list)
    assert out[0]["snippet"] == "S" * 800      # summary 口径，不是 content[:300]
    assert out[0]["title"] == "T"
    assert out[0]["url"] == "https://e.com"
    assert len(calls) == 1
    url, kwargs = calls[0]
    assert url == "https://api.deepseek.com/v1/tools/search"
    assert kwargs["headers"]["Authorization"] == "Bearer sk-test"


def test_tavily_rollback(monkeypatch):
    """行为2：provider=tavily 一键回滚，旧请求/映射契约零差异。"""
    monkeypatch.setattr(settings, "WEB_SEARCH_PROVIDER", "tavily")
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-test")
    payload = {"results": [{"title": "T", "url": "https://e.com", "content": "C" * 500, "score": 0.9}]}
    calls = _patch_post(monkeypatch, payload=payload)

    out = json.loads(web_tools.web_search.func("q"))

    assert isinstance(out, list)
    assert out[0]["snippet"] == "C" * 300
    assert "rerank_score" not in out[0]
    url, kwargs = calls[0]
    assert url == web_tools.TAVILY_API_URL
    assert kwargs["json"] == {"query": "q", "max_results": settings.TAVILY_MAX_RESULTS, "search_depth": "basic"}
    assert kwargs["timeout"] == settings.TAVILY_TIMEOUT


@pytest.mark.parametrize("raw,expect_deepseek", [("", True), ("bogus", True), ("DeepSeek", True), (" TAVILY ", False)])
def test_provider_normalization(monkeypatch, raw, expect_deepseek):
    """行为3：provider 规范化（空/非法/大小写→deepseek，tavily 带空格→tavily）。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-test")
    monkeypatch.setattr(settings, "WEB_SEARCH_PROVIDER", raw)
    calls = _patch_post(monkeypatch, payload={"results": []})

    web_tools.web_search.func("q")

    url, _ = calls[0]
    assert url == ("https://api.deepseek.com/v1/tools/search" if expect_deepseek else web_tools.TAVILY_API_URL)


@pytest.mark.parametrize("base", ["https://api.deepseek.com", "https://api.deepseek.com/v1"])
def test_deepseek_request_contract(monkeypatch, base):
    """行为4：两种 base 写法都收敛到 /v1/tools/search（不出现 /v1/v1），请求体键恰为 query/count/need_content。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "DEEPSEEK_BASE_URL", base)
    monkeypatch.setattr(settings, "DEEPSEEK_SEARCH_TIMEOUT", 20)
    calls = _patch_post(monkeypatch, payload={"results": []})

    web_tools.web_search.func("q")

    url, kwargs = calls[0]
    assert url == "https://api.deepseek.com/v1/tools/search"
    assert "/v1/v1" not in url
    assert kwargs["json"] == {"query": "q", "count": 10, "need_content": False}
    assert kwargs["timeout"] == 20
    assert kwargs["headers"]["Authorization"] == "Bearer sk-test"


def test_deepseek_empty_key(monkeypatch):
    """行为5：空 key 降级含「永久未启用」+「DEEPSEEK_API_KEY」，不发请求、不缓存。"""
    calls = _patch_post(monkeypatch, payload={"results": []})

    out = json.loads(web_tools.web_search.func("q"))

    assert "永久未启用" in out["error"]
    assert "DEEPSEEK_API_KEY" in out["error"]
    assert len(calls) == 0
    assert web_tools._cache == {}


def test_deepseek_empty_results(monkeypatch):
    """行为6：results:[] → 无搜索结果 error，不缓存。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    calls = _patch_post(monkeypatch, payload={"results": []})

    out = json.loads(web_tools.web_search.func("q"))
    assert out["error"] == "无搜索结果"
    web_tools.web_search.func("q")
    assert len(calls) == 2


def test_deepseek_quality_filter_sort(monkeypatch):
    """行为7：rerank<1.0 与 authority==0 丢弃、-1 保留、≤5 条、按 rerank→authority→date 降序。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    results = [
        {"rerank_score": 0.5, "authority": 3, "url": "low_rerank", "summary": "x", "title": "t", "date": None},
        {"rerank_score": 2.0, "authority": 0, "url": "zero_auth", "summary": "x", "title": "t", "date": None},
        {"rerank_score": 2.0, "authority": -1, "url": "unknown_auth", "summary": "x", "title": "t", "date": None},
        {"rerank_score": 2.8, "authority": 2, "url": "top", "summary": "x", "title": "t", "date": "2026-01-01"},
        {"rerank_score": 2.0, "authority": 4, "url": "high_auth", "summary": "x", "title": "t", "date": "2026-02-01"},
        {"rerank_score": 2.0, "authority": 3, "url": "newer", "summary": "x", "title": "t", "date": "2026-03-01"},
        {"rerank_score": 2.0, "authority": 3, "url": "older", "summary": "x", "title": "t", "date": "2026-01-01"},
        {"rerank_score": 1.2, "authority": 1, "url": "tail", "summary": "x", "title": "t", "date": None},
    ]
    _patch_post(monkeypatch, payload={"results": results})

    out = json.loads(web_tools.web_search.func("q"))
    urls = [o["url"] for o in out]

    assert "low_rerank" not in urls
    assert "zero_auth" not in urls
    assert "unknown_auth" in urls
    assert len(out) <= 5
    assert urls[0] == "top"
    assert urls.index("high_auth") < urls.index("newer") < urls.index("older")


def test_deepseek_filter_empty_relax(monkeypatch):
    """行为8：过滤后全空但原始非空 → 放宽按 rerank 取原始 top3，不报无结果。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    results = [{"rerank_score": s, "authority": 2, "url": f"u{s}", "summary": "x", "title": "t", "date": None}
               for s in (0.9, 0.5, 0.7, 0.3)]
    _patch_post(monkeypatch, payload={"results": results})

    out = json.loads(web_tools.web_search.func("q"))

    assert isinstance(out, list)
    assert len(out) == 3
    assert [o["url"] for o in out] == ["u0.9", "u0.7", "u0.5"]
    assert web_tools._cache


@pytest.mark.parametrize("field,value,expect_len", [("summary", "X" * 900, 800), ("snippet", "Y" * 150, 150), ("content", "Z" * 500, 500)])
def test_deepseek_summary_fallback(monkeypatch, field, value, expect_len):
    """行为9：summary→snippet→content 回退链 + cap800 + 扩展字段透传（null 保 null）。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    r = {"rerank_score": 2.0, "authority": 3, "title": "T", "url": "https://e.com", "date": None, "site_name": None}
    r[field] = value
    _patch_post(monkeypatch, payload={"results": [r]})

    out = json.loads(web_tools.web_search.func("q"))

    assert len(out[0]["snippet"]) == expect_len
    assert out[0]["rerank_score"] == 2.0
    assert out[0]["authority"] == 3
    assert out[0]["date"] is None
    assert out[0]["site_name"] is None


def test_query_truncation(monkeypatch):
    """行为10：query>128 截断，缓存 key 用截断值。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    payload = {"results": [{"rerank_score": 2.0, "authority": 3, "title": "T", "url": "https://e.com", "summary": "s", "date": None}]}
    calls = _patch_post(monkeypatch, payload=payload)

    web_tools.web_search.func("a" * 200)
    assert calls[0][1]["json"]["query"] == "a" * 128
    web_tools.web_search.func("a" * 128)
    assert len(calls) == 1


@pytest.mark.parametrize("q", ["", "   "])
def test_empty_query(monkeypatch, q):
    """行为10：空 query guard，不发请求。"""
    calls = _patch_post(monkeypatch, payload={"results": []})
    out = json.loads(web_tools.web_search.func(q))
    assert out["error"] == "query 不能为空"
    assert len(calls) == 0


@pytest.mark.parametrize("status,keyword", [(400, "请求被拒"), (401, "401"), (402, "余额"), (408, "408"), (429, "限流"), (504, "504")])
def test_deepseek_http_errors(monkeypatch, status, keyword):
    """行为11：HTTP 错误分类，全部可重试失败、严禁「永久未启用」、不缓存。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    calls = _patch_post(monkeypatch, payload={"error": {"message": "x"}}, status=status)

    out = json.loads(web_tools.web_search.func("q"))
    assert keyword in out["error"]
    assert out["query"] == "q"
    assert "永久未启用" not in out["error"]
    web_tools.web_search.func("q")
    assert len(calls) == 2


def test_deepseek_timeout(monkeypatch):
    """行为11：超时 error，不含「永久未启用」。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    _patch_post(monkeypatch, timeout=True)
    out = json.loads(web_tools.web_search.func("q"))
    assert "超时" in out["error"]
    assert "永久未启用" not in out["error"]


def test_search_cache_provider_isolation(monkeypatch):
    """行为12：同 provider 同 query 命中缓存；切 provider 不命中旧缓存。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-test")
    payload = {"results": [{"rerank_score": 2.0, "authority": 3, "title": "T", "url": "https://e.com", "summary": "s", "date": None}]}
    calls = _patch_post(monkeypatch, payload=payload)

    r1 = web_tools.web_search.func("q")
    r2 = web_tools.web_search.func("q")
    assert len(calls) == 1 and r2 == r1
    monkeypatch.setattr(settings, "WEB_SEARCH_PROVIDER", "tavily")
    web_tools.web_search.func("q")
    assert len(calls) == 2


def test_search_cache_ttl(monkeypatch):
    """行为12：TTL 过期后重新调用。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    payload = {"results": [{"rerank_score": 2.0, "authority": 3, "title": "T", "url": "https://e.com", "summary": "s", "date": None}]}
    calls = _patch_post(monkeypatch, payload=payload)
    base = 1000.0
    monkeypatch.setattr(web_tools.time, "time", lambda: base)
    web_tools.web_search.func("q")
    assert len(calls) == 1
    monkeypatch.setattr(web_tools.time, "time", lambda: base + 601)
    web_tools.web_search.func("q")
    assert len(calls) == 2


def test_throttle_guard(monkeypatch):
    """行为13：两次真实调用间限速 sleep>0；缓存命中不 sleep。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(web_tools, "MIN_INTERVAL", 1.0)
    sleeps = []
    monkeypatch.setattr(web_tools.time, "sleep", lambda s: sleeps.append(s))
    payload = {"results": [{"rerank_score": 2.0, "authority": 3, "title": "T", "url": "https://e.com", "summary": "s", "date": None}]}
    calls = _patch_post(monkeypatch, payload=payload)

    web_tools.web_search.func("q1")
    web_tools.web_search.func("q2")
    assert len(calls) == 2
    assert any(s > 0 for s in sleeps)
    sleeps.clear()
    web_tools.web_search.func("q1")
    assert len(calls) == 2
    assert not sleeps


# ---------- 阶段 C：web_fetch ----------
def test_fetch_happy_path(monkeypatch):
    """行为16：fetch 回 {title,url,content}，URL={base}/v1/tools/fetch、body={url}、Bearer、timeout25。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "DEEPSEEK_FETCH_TIMEOUT", 25)
    payload = {"title": "页面标题", "content": "# Markdown\n" + "正" * 5000}
    calls = _patch_post(monkeypatch, payload=payload)

    out = json.loads(web_tools.web_fetch.func("https://e.com/page"))

    assert out["title"] == "页面标题"
    assert out["url"] == "https://e.com/page"
    assert out["content"].startswith("# Markdown")
    assert len(calls) == 1
    url, kwargs = calls[0]
    assert url == "https://api.deepseek.com/v1/tools/fetch"
    assert kwargs["json"] == {"url": "https://e.com/page"}
    assert kwargs["headers"]["Authorization"] == "Bearer sk-test"
    assert kwargs["timeout"] == 25


def test_fetch_reports_fetch_time_and_truncated_state(monkeypatch):
    """成功 Fetch 返回 UTC 抓取时间，并明确标记正文未截断。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    _patch_post(monkeypatch, payload={"title": "页面标题", "content": "完整正文"})

    out = json.loads(web_tools.web_fetch.func("https://e.com/page"))

    assert out["fetched_at"].endswith("+00:00")
    assert out["truncated"] is False


@pytest.mark.parametrize("bad_url", ["", "ftp://x", "https://", "https://u:p@x.com", "https://e.com/" + "a" * 8192])
def test_fetch_url_precheck(monkeypatch, bad_url):
    """行为17：非法 URL 预校验，error 含「URL 非法」，不发请求。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    calls = _patch_post(monkeypatch, payload={"title": "T", "content": "x"})
    out = json.loads(web_tools.web_fetch.func(bad_url))
    assert "URL 非法" in out["error"]
    assert len(calls) == 0


def test_fetch_empty_key(monkeypatch):
    """行为18：空 key error 含「未启用」+「DEEPSEEK_API_KEY」，不含「永久未启用」，不发请求。"""
    calls = _patch_post(monkeypatch, payload={"title": "T", "content": "x"})
    out = json.loads(web_tools.web_fetch.func("https://e.com/page"))
    assert "未启用" in out["error"]
    assert "DEEPSEEK_API_KEY" in out["error"]
    assert "永久未启用" not in out["error"]
    assert len(calls) == 0


@pytest.mark.parametrize("status,keyword", [(403, "换源"), (404, "无可用正文"), (402, "余额"), (429, "限流"), (408, "超时"), (504, "服务异常")])
def test_fetch_http_errors(monkeypatch, status, keyword):
    """行为19：fetch HTTP 错误族，带 url、含关键字、不含「永久未启用」、不缓存。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    calls = _patch_post(monkeypatch, payload={"title": "T", "content": "x"}, status=status)
    out = json.loads(web_tools.web_fetch.func("https://e.com/page"))
    assert keyword in out["error"]
    assert out["url"] == "https://e.com/page"
    assert "永久未启用" not in out["error"]
    web_tools.web_fetch.func("https://e.com/page")
    assert len(calls) == 2


def test_fetch_timeout(monkeypatch):
    """行为19：超时 error，不含「永久未启用」。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    _patch_post(monkeypatch, timeout=True)
    out = json.loads(web_tools.web_fetch.func("https://e.com/page"))
    assert "超时" in out["error"]
    assert "永久未启用" not in out["error"]


def test_fetch_empty_content(monkeypatch):
    """行为19：200 但 content 空 → error「空正文」，不缓存。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    calls = _patch_post(monkeypatch, payload={"title": "T", "content": ""})
    out = json.loads(web_tools.web_fetch.func("https://e.com/page"))
    assert "空正文" in out["error"]
    web_tools.web_fetch.func("https://e.com/page")
    assert len(calls) == 2


def test_fetch_content_cap(monkeypatch):
    """行为20：content30000 → 截 20000 + 尾部截断标记；缓存截断后 payload。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    calls = _patch_post(monkeypatch, payload={"title": "T", "content": "x" * 30000})
    out = json.loads(web_tools.web_fetch.func("https://e.com/page"))
    assert out["content"].startswith("x" * 20000)
    assert len(out["content"]) > 20000
    assert "截断" in out["content"]
    assert out["truncated"] is True
    out2 = json.loads(web_tools.web_fetch.func("https://e.com/page"))
    assert len(calls) == 1
    assert out2["content"] == out["content"]


def test_fetch_cache_and_isolation(monkeypatch):
    """行为21：同 url 二次命中；同字符串作 search query 不命中 fetch 缓存（键空间隔离）。"""
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    calls = _patch_post(monkeypatch, payload={"title": "T", "content": "# 正文"})
    u = "https://e.com/page"
    r1 = web_tools.web_fetch.func(u)
    r2 = web_tools.web_fetch.func(u)
    assert len(calls) == 1 and r2 == r1
    web_tools.web_search.func(u)
    assert len(calls) == 2