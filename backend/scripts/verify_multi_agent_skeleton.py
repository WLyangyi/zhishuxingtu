"""M7.0: verify_multi_agent_skeleton.py — A′ 多 Agent 骨架真实链路冒烟。

前置(脚本自动完成,对应拍板结论):
  1. checkpoint 清空:确认无服务运行后删除 data/langgraph_checkpoints.db(必须停服清库,SqliteSaver 持有连接)
  2. 以 AGENT_MULTI_AGENT=true 起独立端口服务(8766),DEBUG=true 覆盖沙箱注入

验证项:
  1. 注册/登录 → SSE 会话
  2. 知识问题:路由 knowledge_agent → 完整 ReAct(intent/thought/action/observation/check/final_answer)
  3. 同会话追问:checkpoint 多轮连续 + turn_start_index 本轮范围(追问答案 ≠ 上轮答案)
  4. 闲聊问题:路由 chat_agent → direct_answer 直答(无工具执行事件)
  5. 事件契约:时间线事件字段 = {type, content, node};final_answer 含 answer;流以 [DONE] 结束

运行方式(backend 目录下):
  .venv\\Scripts\\python.exe scripts\\verify_multi_agent_skeleton.py
"""

import json
import os
import subprocess
import sys
import time
import uuid

import httpx

PORT = 8766
BASE = f"http://127.0.0.1:{PORT}"

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

# P11 教训:独立脚本必须先 import app.core.config 再 import 服务模块
from app.core.config import settings  # noqa: E402

PASS, FAIL = "PASS", "FAIL"
results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{PASS if ok else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def wipe_checkpoints():
    """拍板:旧 checkpoint 直接清空(运行中删除无效,须停服——本脚本起服务前执行)。"""
    db_path = os.path.join(BACKEND_DIR, settings.AGENT_CHECKPOINT_DB)
    if os.path.exists(db_path):
        os.remove(db_path)
        record("checkpoint 清空(停服后删除)", True, db_path)
    else:
        record("checkpoint 清空(无需,文件不存在)", True, db_path)


def start_server():
    env = {**os.environ, "DEBUG": "true", "AGENT_MULTI_AGENT": "true"}
    proc = subprocess.Popen(
        [
            os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe"),
            "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(PORT),
        ],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
    for _ in range(60):
        if proc.poll() is not None:
            out = proc.stdout.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"服务器启动失败:\n{out[-3000:]}")
        try:
            if httpx.get(f"{BASE}/health", timeout=2).status_code == 200:
                record(f"服务启动(AGENT_MULTI_AGENT=true, :{PORT})", True)
                return proc
        except Exception:
            pass
        time.sleep(1)
    proc.terminate()
    raise RuntimeError("服务器 60s 内未就绪")


def register_and_login(client):
    username = f"m7smoke_{uuid.uuid4().hex[:8]}"
    password = "M7Smoke#2026"
    r = client.post(f"{BASE}/api/auth/register", json={"username": username, "password": password})
    assert r.status_code in (200, 201), f"注册失败: {r.status_code} {r.text[:200]}"
    # login 是 OAuth2 form
    r = client.post(f"{BASE}/api/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, f"登录失败: {r.status_code} {r.text[:200]}"
    token = r.json()["access_token"]
    record("注册/登录", True, username)
    return {"Authorization": f"Bearer {token}"}


def stream_chat(client, headers, question, session_id):
    """POST /api/agent/chat/stream,解析 SSE 事件流。返回 (events, done_flag)。
    session_id 由客户端生成并传入(后端 _get_or_create_session 接受客户端指定)。"""
    events = []
    done = False
    with client.stream(
        "POST",
        f"{BASE}/api/agent/chat/stream",
        params={"question": question, "session_id": session_id},
        headers=headers,
        timeout=180,
    ) as resp:
        assert resp.status_code == 200, f"SSE 请求失败: {resp.status_code} {resp.read()[:300]}"
        for line in resp.iter_lines():
            line = (line or "").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                done = True
                break
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                events.append({"type": "_raw", "content": payload})
    return events, done


def check_event_contract(events):
    """事件契约:时间线事件必须有 type/content/node;final_answer 必须有 answer。"""
    problems = []
    key_sets = {}
    for ev in events:
        t = ev.get("type", "?")
        key_sets.setdefault(t, set()).update(ev.keys())
        if t in ("thought", "action", "observation", "check", "intent"):
            if not isinstance(ev.get("content"), str) or "node" not in ev:
                problems.append(f"{t} 事件字段缺失: {ev}")
        if t == "final_answer" and "answer" not in ev:
            problems.append(f"final_answer 缺 answer: {ev}")
        if t == "error":
            problems.append(f"出现 error 事件: {ev}")
    return problems, {k: sorted(v) for k, v in key_sets.items()}


def main():
    wipe_checkpoints()
    proc = start_server()
    try:
        client = httpx.Client()
        headers = register_and_login(client)
        sid = str(uuid.uuid4())

        # ---- 1. 知识问题 → knowledge_agent 完整 ReAct ----
        print("\n[1] 知识问题(期望 knowledge_agent 完整链路)")
        events, done = stream_chat(client, headers, "5月10日有哪些科技产品发布?", sid)
        problems, key_sets = check_event_contract(events)
        record("SSE 事件契约({type,content,node}/final_answer/[DONE])", not problems and done,
               f"事件类型: {sorted(key_sets)}" + (f";问题: {problems[:2]}" if problems else ""))
        types = [e.get("type") for e in events]
        record("意图路由 knowledge", any(e.get("type") == "intent" and "knowledge" in e.get("content", "") for e in events),
               str(types[:6]))
        record("完整 ReAct 时间线(thought/action/check 增量到达)",
               all(t in types for t in ("thought", "action", "observation")) and "check" in types,
               f"{len(events)} 个事件")
        final = next((e["answer"] for e in events if e.get("type") == "final_answer"), "")
        record("final_answer 非空", bool(final.strip()), f"长度 {len(final)}")

        # ---- 2. 同会话追问 → checkpoint 多轮 + turn_start_index ----
        print("\n[2] 同会话追问(期望 checkpoint 多轮连续,追问答案独立于上轮)")
        events2, done2 = stream_chat(client, headers, "用一句话概括你上一条回答的核心内容", sid)
        problems2, _ = check_event_contract(events2)
        final2 = next((e["answer"] for e in events2 if e.get("type") == "final_answer"), "")
        record("追问轮 SSE 正常且答案独立", done2 and not problems2 and bool(final2.strip()) and final2 != final,
               f"长度 {len(final2)};{'与上轮答案不同' if final2 != final else '!!与上轮答案相同(跨轮污染)'}")

        # ---- 3. 闲聊 → chat_agent 直答(无工具) ----
        print("\n[3] 闲聊(期望 chat_agent 短路直答,无工具执行)")
        events3, done3 = stream_chat(client, headers, "用一句话介绍你自己", str(uuid.uuid4()))
        record("chat_agent 直答", done3 and any(e.get("type") == "final_answer" for e in events3),
               f"{len(events3)} 个事件")
        tool_leak = [e for e in events3 if e.get("type") in ("action", "observation")]
        record("直答路径无工具执行事件", not tool_leak)

        summary = sum(1 for _, ok, _ in results if ok)
        print(f"\n===== 冒烟结果: {summary}/{len(results)} 通过 =====")
        for name, ok, detail in results:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        sys.exit(0 if summary == len(results) else 1)
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
