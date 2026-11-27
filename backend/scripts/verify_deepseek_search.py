# -*- coding: utf-8 -*-
"""联网搜索 DeepSeek 化冒烟:真实 Search/Fetch API 四项 check(仿 verify_deepseek_tools.py)。

用法(backend 目录下):
    .venv\\Scripts\\python.exe scripts/verify_deepseek_search.py

前置:WEB_SEARCH_PROVIDER=deepseek(默认)且 DEEPSEEK_API_KEY 已配置;缺失 exit(1)。
4 项检查(全过才继续,任一失败 → 停下反馈):
  1. search 真实调用回非空 list 且首条 snippet>300(summary 口径,非旧 300 字 snippet)
  2. 请求 URL == {base}/v1/tools/search(不出现 /v1/v1)
  3. fetch 对首条 url 抓全文回非空 content
  4. 二次同 query 命中缓存(无新增真实请求 + 结果一致)
"""
import json
import os
import sys

# 本机 Windows 裸 import 会卡 WMI 查询,进程内注入 platform workaround(同 tests 口径)
import platform

sys.modules.setdefault("transformers", None)
platform.system = lambda: "Windows"
platform.win32_ver = lambda *a, **k: ("", "", "", "")
platform.machine = lambda: "AMD64"
platform.platform = lambda *a, **k: "Windows-AMD64"
platform.uname = lambda: ("Windows", "", "", "", "AMD64", "")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402
import app.services.tools.web_tools as wt  # noqa: E402

QUERY = "Python 3.12 官方主要新特性"
PASS, FAIL = "PASS", "FAIL"
results = []
seen_urls = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{PASS if ok else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def install_recorder():
    """包裹 httpx.post 记录真实请求 URL,仍委托真实 post(冒烟要真打 API)。"""
    real_post = wt.httpx.post

    def recording_post(url, *a, **k):
        seen_urls.append(url)
        return real_post(url, *a, **k)

    wt.httpx.post = recording_post


def expected_search_url():
    base = (settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com").rstrip("/")
    return f"{base}/tools/search" if base.endswith("/v1") else f"{base}/v1/tools/search"


def main() -> int:
    provider = wt._resolve_provider()
    if provider != "deepseek":
        print(f"[失败] WEB_SEARCH_PROVIDER={provider},本冒烟仅验证 deepseek 通道。")
        return 1
    if not settings.DEEPSEEK_API_KEY:
        print("[失败] DEEPSEEK_API_KEY 未配置。")
        return 1

    wt._cache.clear()
    wt._last_call_ts = 0.0
    install_recorder()
    print(f"provider=deepseek base={settings.DEEPSEEK_BASE_URL} query={QUERY!r}")
    print("=" * 50)

    # 1. search 真实调用回非空 list 且 snippet>300
    print("\n[1/4] search 真实调用回非空 list 且首条 snippet>300(summary 口径) ...")
    r1 = wt.web_search.func(QUERY)
    try:
        data = json.loads(r1)
    except Exception as e:
        record("search 返回合法 JSON", False, str(e)[:80])
        data = None
    if isinstance(data, list) and data:
        snippet = data[0].get("snippet", "")
        record("search 非空 list 且首条 snippet>300", len(snippet) > 300,
               f"{len(data)} 条, 首条 snippet {len(snippet)} 字")
    else:
        record("search 非空 list 且首条 snippet>300", False, str(data)[:120])

    # 2. URL 契约
    print("\n[2/4] 请求 URL == {base}/v1/tools/search(无 /v1/v1) ...")
    exp = expected_search_url()
    first = seen_urls[0] if seen_urls else None
    record("search URL 契约", first == exp and "/v1/v1" not in (first or ""),
           f"seen={first} exp={exp}")

    # 3. fetch 首条 url 抓全文
    print("\n[3/4] fetch 首条 url 抓全文回非空 content ...")
    if isinstance(data, list) and data and data[0].get("url"):
        url = data[0]["url"]
        try:
            fd = json.loads(wt.web_fetch.func(url))
        except Exception:
            fd = {}
        content = fd.get("content", "") if isinstance(fd, dict) else ""
        err = fd.get("error") if isinstance(fd, dict) else None
        record("fetch 回非空 content", bool(content),
               f"url={url[:60]} content {len(content)} 字" + (f" err={err}" if err else ""))
    else:
        record("fetch 回非空 content", False, "search 无可用 url,跳过")

    # 4. 二次同 query 命中缓存
    print("\n[4/4] 二次同 query 命中缓存(无新增请求 + 结果一致) ...")
    before = len(seen_urls)
    r2 = wt.web_search.func(QUERY)
    record("二次同 query 命中缓存", len(seen_urls) == before and r2 == r1,
           f"新增请求 {len(seen_urls) - before}, 一致={r2 == r1}")

    print("\n" + "=" * 50)
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, _ in results:
        print(f"  [{PASS if ok else FAIL}] {name}")
    print(f"共 {len(results)} 项,通过 {passed} 项")
    if passed == len(results):
        print("[deepseek-search] 4 项全部通过。联网 DeepSeek 化主链路可用。")
        return 0
    print(f"[deepseek-search] {passed}/{len(results)} 通过,未全部通过。按计划停下,处理后再继续。")
    return 1


if __name__ == "__main__":
    sys.exit(main())