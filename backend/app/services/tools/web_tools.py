import json
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from langchain_core.tools import tool

TAVILY_API_URL = "https://api.tavily.com/search"
SNIPPET_LEN = 300    # tavily 单条结果摘要长度，与 search_notes 的 snippet 口径一致
CACHE_TTL = 600      # 查询缓存有效期（秒）：同一 query 10 分钟内直接返回缓存
MIN_INTERVAL = 1.0   # 相邻两次真实 API 调用的最小间隔（秒），保护额度限速
CACHE_MAX_ENTRIES = 200

# DeepSeek Search 算法参数（非部署配置，不进 settings）
DEEPSEEK_SEARCH_COUNT = 10      # 请求候选数：计费按成功请求次而非条数，多拿候选不加钱
WEB_SEARCH_TOP_K = 5            # 过滤排序后输出条数（对齐旧 TAVILY_MAX_RESULTS 体量）
MIN_RERANK = 1.0                # 相关性地板，低于此丢弃（1.5 是"优质"线非硬门槛）
DEEPSEEK_SNIPPET_CAP = 800      # summary→snippet 上限
QUERY_MAX_LEN = 128             # DeepSeek query 硬限制，超出截断不拒绝
FETCH_CONTENT_CAP = 20000       # web_fetch 正文工具层截断上限（尺寸压缩交给 offload）
URL_MAX_LEN = 8192              # web_fetch URL 长度上限

_cache: dict = {}    # namespaced key -> (timestamp, payload)
_cache_lock = threading.Lock()
_last_call_ts = 0.0


def _cache_get(key: str):
    """命中未过期缓存则返回 payload，否则 None。"""
    with _cache_lock:
        hit = _cache.get(key)
        if hit is None:
            return None
        ts, payload = hit
        if time.time() - ts < CACHE_TTL:
            return payload
        _cache.pop(key, None)
    return None


def _cache_put(key: str, payload: str):
    """写入缓存（仅缓存成功结果，失败不缓存避免瞬时故障粘住）。"""
    with _cache_lock:
        if len(_cache) >= CACHE_MAX_ENTRIES:
            _cache.clear()  # 简单防膨胀：超过上限整体清空
        _cache[key] = (time.time(), payload)


def _throttle():
    """相邻两次真实 API 调用保持最小间隔：锁内占位、锁外等待，不阻塞缓存读。"""
    global _last_call_ts
    with _cache_lock:
        now = time.monotonic()
        wait = MIN_INTERVAL - (now - _last_call_ts)
        _last_call_ts = max(now, _last_call_ts + MIN_INTERVAL)
    if wait > 0:
        time.sleep(wait)


def _resolve_provider() -> str:
    """联网搜索 provider 规范化：tavily|deepseek，非法/缺失回退 deepseek（延迟读 settings）。"""
    from app.core.config import settings

    raw = str(getattr(settings, "WEB_SEARCH_PROVIDER", "deepseek")).strip().lower()
    return raw if raw in ("tavily", "deepseek") else "deepseek"


def _deepseek_url(path: str) -> str:
    """拼 DeepSeek 工具端点，兼容 base_url 含/不含 /v1 两种写法（不出现 /v1/v1）。"""
    from app.core.config import settings

    base = (settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com").rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/tools/{path}"
    return f"{base}/v1/tools/{path}"


def _search_error_text(status: int) -> str:
    """DeepSeek HTTP 错误分类：全部可重试失败，严禁「永久未启用」（那是空 key 专用契约）。"""
    if status == 402:
        return "web_search 请求被拒: HTTP 402 余额不足,请充值后重试;本轮改用知识库检索"
    if status == 429:
        return "web_search 请求被拒: HTTP 429 限流,请稍后重试"
    if status == 401:
        return "web_search 请求被拒: HTTP 401 请检查 DEEPSEEK_API_KEY"
    return f"web_search 请求被拒: HTTP {status}"


def _map_deepseek_results(results: list) -> list:
    """质量过滤 + 排序 + 截断 + summary 映射。过滤后全空但原始非空→放宽原始 top3。"""
    if not results:
        return []

    def rs(r):
        return r.get("rerank_score") or 0.0

    def au(r):
        return r.get("authority")

    # authority==0 丢弃、==-1（未知）保留；rerank<1.0 丢弃
    filtered = [r for r in results if rs(r) >= MIN_RERANK and au(r) != 0]
    if filtered:
        pool = sorted(
            filtered,
            key=lambda r: (rs(r), max(au(r) or 0, 0), r.get("date") or ""),
            reverse=True,
        )[:WEB_SEARCH_TOP_K]
    else:
        pool = sorted(results, key=rs, reverse=True)[:3]

    out = []
    for r in pool:
        text = r.get("summary") or r.get("snippet") or r.get("content") or ""
        out.append(
            {
                "title": (r.get("title") or "")[:100],
                "url": r.get("url") or "",
                "snippet": text[:DEEPSEEK_SNIPPET_CAP],
                "rerank_score": r.get("rerank_score"),
                "authority": r.get("authority"),
                "date": r.get("date"),
                "site_name": r.get("site_name"),
            }
        )
    return out


def _search_tavily(query: str):
    """Tavily 回滚分支：原样保留旧请求/映射/异常文案，返回 (items|None, error|None)。"""
    from app.core.config import settings

    try:
        resp = httpx.post(
            TAVILY_API_URL,
            headers={"Authorization": f"Bearer {settings.TAVILY_API_KEY}"},
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
        return None, {"error": f"web_search 超时({settings.TAVILY_TIMEOUT}s)", "query": query}
    except httpx.HTTPStatusError as e:
        return None, {"error": f"web_search 请求被拒: HTTP {e.response.status_code}", "query": query}
    except Exception as e:
        return None, {"error": f"web_search 失败: {type(e).__name__}", "query": query}

    out = []
    for r in data.get("results", []):
        out.append(
            {
                "title": (r.get("title") or "")[:100],
                "url": r.get("url") or "",
                "snippet": (r.get("content") or "")[:SNIPPET_LEN],
            }
        )
    return out, None


def _search_deepseek(query: str):
    """DeepSeek Search 分支：返回 (items|None, error|None)。"""
    from app.core.config import settings

    try:
        resp = httpx.post(
            _deepseek_url("search"),
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
            json={"query": query, "count": DEEPSEEK_SEARCH_COUNT, "need_content": False},
            timeout=settings.DEEPSEEK_SEARCH_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        return None, {"error": f"web_search 超时({settings.DEEPSEEK_SEARCH_TIMEOUT}s)", "query": query}
    except httpx.HTTPStatusError as e:
        return None, {"error": _search_error_text(e.response.status_code), "query": query}
    except Exception as e:
        return None, {"error": f"web_search 失败: {type(e).__name__}", "query": query}

    return _map_deepseek_results(data.get("results", [])), None


@tool
def web_search(query: str) -> str:
    """联网搜索最新信息。返回 JSON 数组,每项含 title/url/snippet（deepseek 源附 rerank_score/authority/date/site_name）。

    query≤128字符。适合知识库中没有的时效性问题;知识库相关的问题优先用 search_notes。
    """
    from app.core.config import settings

    query = (query or "").strip()[:QUERY_MAX_LEN]
    if not query:
        return json.dumps({"error": "query 不能为空"}, ensure_ascii=False)

    provider = _resolve_provider()
    api_key = settings.DEEPSEEK_API_KEY if provider == "deepseek" else settings.TAVILY_API_KEY
    if not api_key:
        # 永久不可用:明确告知 agent 不要再重试（「永久未启用」子串是编排熔断契约）。
        key_name = "DEEPSEEK_API_KEY" if provider == "deepseek" else "TAVILY_API_KEY"
        return json.dumps(
            {
                "error": f"web_search 永久未启用(.env 缺少 {key_name})。"
                "请勿再次调用 web_search;应改从知识库检索,或直接告知用户联网搜索未启用。"
            },
            ensure_ascii=False,
        )

    cache_key = f"search:{provider}:{query}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    _throttle()

    if provider == "deepseek":
        items, err = _search_deepseek(query)
    else:
        items, err = _search_tavily(query)

    if err is not None:
        return json.dumps(err, ensure_ascii=False)
    if not items:
        return json.dumps({"error": "无搜索结果", "query": query}, ensure_ascii=False)

    payload = json.dumps(items, ensure_ascii=False)
    _cache_put(cache_key, payload)
    return payload


def _validate_fetch_url(url: str):
    """URL 预校验：非法直接 error，不发请求/不计费/不烧熔断。返回 error 文案或 None。"""
    if not url:
        return "web_fetch URL 非法: 为空"
    if len(url) > URL_MAX_LEN:
        return f"web_fetch URL 非法: 超过 {URL_MAX_LEN} 字符"
    if not url.startswith(("http://", "https://")):
        return "web_fetch URL 非法: 仅支持 http(s)"
    parsed = urlparse(url)
    if not parsed.hostname:
        return "web_fetch URL 非法: 缺少 host"
    if parsed.username or parsed.password:
        return "web_fetch URL 非法: 不允许 userinfo"
    return None


def _fetch_error_text(status: int) -> str:
    """fetch HTTP 错误分类：均带换源/重试引导，严禁「永久未启用」（空 key 专用契约）。"""
    if status == 403:
        return "web_fetch 被安全策略拒绝(403),请换源"
    if status == 404:
        return "web_fetch 无可用正文(404),请换源"
    if status == 402:
        return "web_fetch 余额不足(402),本轮改用知识库检索"
    if status == 429:
        return "web_fetch 限流(429),请稍后重试"
    if status == 408 or status >= 500:
        return f"web_fetch 下游超时/服务异常({status}),请稍后重试或换源"
    return f"web_fetch 请求被拒: HTTP {status}"


@tool
def web_fetch(url: str) -> str:
    """抓取网页正文(Markdown)。在 web_search 选中结果后,需要正文细节或深入验证时调用。

    返回 {title,url,content}。403/404 请换源,不要重复抓同一 url;正文超长会截断。
    """
    from app.core.config import settings

    url = (url or "").strip()
    invalid = _validate_fetch_url(url)
    if invalid:
        return json.dumps({"error": invalid, "url": url}, ensure_ascii=False)
    if not settings.DEEPSEEK_API_KEY:
        # 不含「永久未启用」:fetch 失败常是 url 级,靠通用 MAX_TOOL_FAILURES 熔断,换源即可。
        return json.dumps(
            {"error": "web_fetch 未启用(.env 缺少 DEEPSEEK_API_KEY)", "url": url},
            ensure_ascii=False,
        )

    cache_key = f"fetch:{url}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    _throttle()
    try:
        resp = httpx.post(
            _deepseek_url("fetch"),
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
            json={"url": url},
            timeout=settings.DEEPSEEK_FETCH_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        return json.dumps(
            {"error": f"web_fetch 超时({settings.DEEPSEEK_FETCH_TIMEOUT}s)", "url": url},
            ensure_ascii=False,
        )
    except httpx.HTTPStatusError as e:
        return json.dumps(
            {"error": _fetch_error_text(e.response.status_code), "url": url},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps(
            {"error": f"web_fetch 失败: {type(e).__name__}", "url": url}, ensure_ascii=False
        )

    content = data.get("content") or ""
    if not content:
        return json.dumps({"error": "web_fetch 返回空正文", "url": url}, ensure_ascii=False)
    truncated = len(content) > FETCH_CONTENT_CAP
    if truncated:
        content = content[:FETCH_CONTENT_CAP] + "\n…[正文超长已截断,需要更多细节请换源或缩小范围]"

    payload = json.dumps(
        {
            "title": data.get("title") or "",
            "url": url,
            "content": content,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "truncated": truncated,
        },
        ensure_ascii=False,
    )
    _cache_put(cache_key, payload)
    return payload
