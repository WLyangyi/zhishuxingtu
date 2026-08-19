"""M3-2: verify_web_search.py — web_search(Tavily) agent 工具 + MCP 端双验证。

两种模式自动切换：
  - TAVILY_API_KEY 未配置：验证优雅降级（工具返回明确"未启用"提示，不抛异常），agent/MCP 链路不受阻
  - TAVILY_API_KEY 已配置：全量验证（真实搜索 + TTL 缓存 + MCP 端调用）

验证项：
  1. agent 工具直调 web_search（真实结果或降级提示）
  2. TTL 缓存生效（同 query 第二次调用命中缓存，返回一致且不再发请求）
  3. MCP 端 call_tool('web_search') 与 agent 工具行为一致

运行方式（在 backend 目录下）：
  .venv\\Scripts\\python.exe scripts\\verify_web_search.py
"""

import asyncio
import json
import os
import subprocess
import sys
import time

import httpx

PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
MCP_URL = f"{BASE}/mcp"
QUERY = "FastAPI 最新版本特性"

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

# P11 教训：独立脚本必须先 import app.core.config 再 import 服务模块
from app.core.config import settings  # noqa: E402

MCP_API_KEY = settings.MCP_API_KEY
TAVILY_KEY = settings.TAVILY_API_KEY

PASS, FAIL = "PASS", "FAIL"
results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{PASS if ok else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def start_server():
    proc = subprocess.Popen(
        [
            os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe"),
            "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(PORT),
        ],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    for _ in range(60):
        if proc.poll() is not None:
            out = proc.stdout.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"服务器启动失败:\n{out[-3000:]}")
        try:
            if httpx.get(f"{BASE}/health", timeout=2).status_code == 200:
                return proc
        except Exception:
            pass
        time.sleep(1)
    proc.terminate()
    raise RuntimeError("服务器 60s 内未就绪")


def test_direct_tool():
    """agent 工具直调（进程内）。"""
    from app.services.tools.web_tools import web_search, _cache

    r1 = web_search.func(QUERY)
    try:
        data = json.loads(r1)
    except Exception:
        record("web_search 返回合法 JSON", False, "解析失败")
        return None

    record("web_search 返回合法 JSON", True)

    if not TAVILY_KEY:
        degraded = isinstance(data, dict) and "TAVILY_API_KEY" in data.get("error", "")
        record("key 缺失时优雅降级(明确提示,不抛异常)", degraded, str(data.get("error", ""))[:60])
        return None

    is_real = isinstance(data, list) and len(data) > 0 and "url" in data[0]
    record("真实搜索返回结果数组", is_real, f"{len(data) if isinstance(data, list) else 0} 条")

    # TTL 缓存：同 query 第二次调用应命中缓存（缓存条目存在 + 返回一致 + 无新增真实调用）
    cache_size_before = len(_cache)
    r2 = web_search.func(QUERY)
    hit_cache = len(_cache) == cache_size_before and r2 == r1
    record("TTL 缓存命中(同 query 直接返回缓存)", hit_cache,
           f"cache={len(_cache)} 条, 结果一致={r2 == r1}")
    return data


async def test_mcp_web_search():
    """MCP 端 call_tool('web_search')。"""
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport

    transport = StreamableHttpTransport(
        url=MCP_URL,
        headers={"Authorization": f"Bearer {MCP_API_KEY}"},
    )
    async with Client(transport) as client:
        result = await client.call_tool("web_search", {"query": QUERY})
        text = result.content[0].text if result.content else ""
        try:
            data = json.loads(text)
        except Exception:
            record("MCP 端 web_search 返回合法 JSON", False)
            return

        record("MCP 端 web_search 返回合法 JSON", True)
        if not TAVILY_KEY:
            degraded = isinstance(data, dict) and "TAVILY_API_KEY" in data.get("error", "")
            record("MCP 端 key 缺失时优雅降级一致", degraded)
        else:
            ok = isinstance(data, list) and len(data) > 0 and "url" in data[0]
            record("MCP 端真实搜索与 agent 工具行为一致", ok,
                   f"{len(data)} 条" if ok else str(data)[:80])


async def main():
    if not MCP_API_KEY:
        print("[SKIP] .env 未配置 MCP_API_KEY，无法验证（先跑 verify_mcp_server.py）")
        return

    mode = "全量验证(真实 Tavily 搜索)" if TAVILY_KEY else "降级验证(TAVILY_API_KEY 未配置)"
    print(f"== 1. agent 工具直调 [{mode}] ==")
    test_direct_tool()

    print("== 2. 启动测试服务器 + MCP 端验证 ==")
    proc = start_server()
    try:
        await test_mcp_web_search()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()

    print("\n========== 验证汇总 ==========")
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"  {PASS if ok else FAIL}  {name}")
    print(f"共 {len(results)} 项，通过 {passed} 项")
    if not TAVILY_KEY:
        print("\n提示: .env 填入 TAVILY_API_KEY 并重启后端后，重跑本脚本做全量验证")
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
