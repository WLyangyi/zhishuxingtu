"""M3-1: verify_mcp_server.py — FastMCP /mcp 端点 + API Key 认证端到端验证。

验证项（对应实施计划 M3-1）：
  1. MCP_API_KEY 未认证请求 → 401（fail-closed）
  2. 错误 API Key → 401
  3. 正确 Bearer Key → MCP 握手成功（fastmcp Client）
  4. list_tools 返回 5 个与 agent 共享的只读工具
  5. call_tool('list_tags') 实际执行并返回数据
  6. 普通 API（/health）不受 MCP 中间件影响

运行方式（在 backend 目录下）：
  .venv\\Scripts\\python.exe scripts\\verify_mcp_server.py
"""

import asyncio
import os
import subprocess
import sys
import time

import httpx

# 独立端口，避免与开发服务器(:8000)冲突
PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
MCP_URL = f"{BASE}/mcp"

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

# P11 教训：独立脚本必须先 import app.core.config 再 import 服务模块
from app.core.config import settings  # noqa: E402

MCP_API_KEY = settings.MCP_API_KEY

PASS, FAIL = "PASS", "FAIL"
results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{PASS if ok else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def start_server():
    """在独立端口启动 uvicorn 子进程（cwd=backend，保证相对路径 DATABASE_URL 正确，P15）。"""
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
    # 等待 /health 就绪
    for _ in range(60):
        if proc.poll() is not None:
            out = proc.stdout.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"服务器启动失败:\n{out[-3000:]}")
        try:
            r = httpx.get(f"{BASE}/health", timeout=2)
            if r.status_code == 200:
                return proc
        except Exception:
            pass
        time.sleep(1)
    proc.terminate()
    raise RuntimeError("服务器 60s 内未就绪")


async def test_auth():
    """认证中间件测试：无 key / 错误 key 均 401。"""
    async with httpx.AsyncClient(timeout=10) as client:
        # 1. 无认证
        r = await client.post(MCP_URL, json={"jsonrpc": "2.0", "method": "initialize", "id": 1})
        record("无认证访问 /mcp 被拒(401)", r.status_code == 401, f"status={r.status_code}")
        # 2. 错误 key
        r = await client.post(
            MCP_URL,
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
            headers={"Authorization": "Bearer wrong-key-xxx"},
        )
        record("错误 API Key 被拒(401)", r.status_code == 401, f"status={r.status_code}")
        # 3. 普通 API 不受影响
        r = await client.get(f"{BASE}/health")
        record("/health 不受 MCP 中间件影响", r.status_code == 200, f"status={r.status_code}")


async def test_mcp_handshake():
    """fastmcp Client 完整 MCP 握手：list_tools + call_tool。"""
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport

    # 4. 无 key 的 MCP 客户端无法建立会话
    try:
        async with Client(StreamableHttpTransport(url=MCP_URL)) as client:
            await client.list_tools()
        record("无 key 的 MCP Client 无法连接", False, "竟然连上了")
    except Exception as e:
        record("无 key 的 MCP Client 无法连接", True, f"{type(e).__name__}")

    # 5-6. 正确 key：握手 + list_tools
    transport = StreamableHttpTransport(
        url=MCP_URL,
        headers={"Authorization": f"Bearer {MCP_API_KEY}"},
    )
    async with Client(transport) as client:
        tools = await client.list_tools()
        tool_names = sorted(t.name for t in tools)
        expected = sorted(["search_notes", "get_note", "get_graph_neighbors", "list_tags", "list_folders", "web_search"])
        record(
            "list_tools 返回 6 个共享只读工具",
            tool_names == expected,
            f"tools={tool_names}",
        )

        # 7. 实际调用一个工具
        result = await client.call_tool("list_tags", {})
        text = result.content[0].text if result.content else ""
        record(
            "call_tool('list_tags') 执行成功",
            len(text) > 0,
            f"返回 {len(text)} 字符",
        )

        # 8. 带 schema 参数的工具调用（search_notes）
        result = await client.call_tool("search_notes", {"query": "测试", "top_k": 3})
        text = result.content[0].text if result.content else ""
        record(
            "call_tool('search_notes') 执行成功",
            len(text) > 0,
            f"返回 {len(text)} 字符",
        )


async def main():
    if not MCP_API_KEY:
        print("[SKIP] .env 未配置 MCP_API_KEY，无法验证")
        return

    print(f"== 1. 启动测试服务器 :{PORT} ==")
    proc = start_server()
    try:
        print("== 2. API Key 认证测试 ==")
        await test_auth()
        print("== 3. MCP 握手 / 工具调用测试 ==")
        await test_mcp_handshake()
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
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
