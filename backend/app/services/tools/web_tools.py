import json
import threading
import time

import httpx
from langchain_core.tools import tool

TAVILY_API_URL = "https://api.tavily.com/search"
SNIPPET_LEN = 300    # 单条结果摘要长度，与 search_notes 的 snippet 口径一致
CACHE_TTL = 600      # 查询缓存有效期（秒）：同一 query 10 分钟内直接返回缓存
MIN_INTERVAL = 1.0   # 相邻两次真实 API 调用的最小间隔（秒），保护免费额度限速
CACHE_MAX_ENTRIES = 200

_cache: dict = {}    # query -> (timestamp, payload)
_cache_lock = threading.Lock()
_last_call_ts = 0.0


def _cache_get(query: str):
    """命中未过期缓存则返回 payload，否则 None。"""
    with _cache_lock:
        hit = _cache.get(query)
        if hit is None:
            return None
        ts, payload = hit
        if time.time() - ts < CACHE_TTL:
            return payload
        _cache.pop(query, None)
    return None


def _cache_put(query: str, payload: str):
    """写入缓存（仅缓存成功结果，失败不缓存避免瞬时故障粘住）。"""
    with _cache_lock:
        if len(_cache) >= CACHE_MAX_ENTRIES:
            _cache.clear()  # 简单防膨胀：超过上限整体清空
        _cache[query] = (time.time(), payload)


def _throttle():
    """相邻两次真实 API 调用保持最小间隔：锁内占位、锁外等待，不阻塞缓存读。"""
    global _last_call_ts
    with _cache_lock:
        now = time.monotonic()
        wait = MIN_INTERVAL - (now - _last_call_ts)
        _last_call_ts = max(now, _last_call_ts + MIN_INTERVAL)
    if wait > 0:
        time.sleep(wait)


@tool
def web_search(query: str) -> str:
    """联网搜索最新信息(Tavily)。返回 JSON 数组,每项含 title/url/snippet(≤300字)。

    适合知识库中没有的时效性问题;知识库相关的问题优先用 search_notes。
    """
    from app.core.config import settings

    query = (query or "").strip()
    if not query:
        return json.dumps({"error": "query 不能为空"}, ensure_ascii=False)

    api_key = settings.TAVILY_API_KEY
    if not api_key:
        return json.dumps(
            {
                "error": "web_search 未启用: .env 缺少 TAVILY_API_KEY"
                "(在 https://tavily.com 免费注册获取并填入,重启后端后生效)"
            },
            ensure_ascii=False,
        )

    cached = _cache_get(query)
    if cached is not None:
        return cached

    _throttle()

    try:
        resp = httpx.post(
            TAVILY_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "query": query,
                "max_results": settings.TAVILY_MAX_RESULTS,
                "search_depth": "basic",
            },
            timeout=settings.TAVILY_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        return json.dumps(
            {"error": f"web_search 超时({settings.TAVILY_TIMEOUT}s)", "query": query},
            ensure_ascii=False,
        )
    except httpx.HTTPStatusError as e:
        return json.dumps(
            {"error": f"web_search 请求被拒: HTTP {e.response.status_code}", "query": query},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps(
            {"error": f"web_search 失败: {type(e).__name__}", "query": query},
            ensure_ascii=False,
        )

    out = []
    for r in data.get("results", []):
        out.append(
            {
                "title": (r.get("title") or "")[:100],
                "url": r.get("url") or "",
                "snippet": (r.get("content") or "")[:SNIPPET_LEN],
            }
        )

    if not out:
        return json.dumps({"error": "无搜索结果", "query": query}, ensure_ascii=False)

    payload = json.dumps(out, ensure_ascii=False)
    _cache_put(query, payload)
    return payload
