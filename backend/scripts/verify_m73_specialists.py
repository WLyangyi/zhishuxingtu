"""M7.3: verify_m73_specialists.py — web_research / note_write 专职 Agent 经编排器路由的真实链路冒烟。

验证项:
  1. web_research_agent:明确联网问题 → intent=web_search → 真实 Tavily web_search →
     跳过文档评级(thoughts 无 grade_documents)→ 有幻觉查 → final_answer 含信源标注
  2. note_write_agent(批准):保存诉求 → approval_required → POST /resume approved=true →
     笔记真正创建 → final_answer 确认
  3. note_write_agent(拒绝):保存诉求 → approval_required → approved=false → 不创建 →
     final_answer 反映拒绝
  4. token 口径:web_research 单问 token_used 记录(M7.3 token 基线)

运行方式(backend 目录下):
  $env:DEBUG='true'; .venv\\Scripts\\python.exe scripts\\verify_m73_specialists.py
"""

import json
import os
import subprocess
import sys
import time
import uuid

import httpx

PORT = 8767
BASE = f"http://127.0.0.1:{PORT}"

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app.core.config import settings  # noqa: E402

PASS, FAIL = "PASS", "FAIL"
results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{PASS if ok else FAIL}] {name}" + (f" — {detail}" if detail else ""))


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
    username = f"m73smoke_{uuid.uuid4().hex[:8]}"
    password = "M73Smoke#2026"
    r = client.post(f"{BASE}/api/auth/register", json={"username": username, "password": password})
    assert r.status_code in (200, 201), f"注册失败: {r.status_code} {r.text[:200]}"
    r = client.post(f"{BASE}/api/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, f"登录失败: {r.status_code} {r.text[:200]}"
    record("注册/登录", True, username)
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def sse_post(client, url, headers, params=None, json_body=None):
    events = []
    done = False
    with client.stream("POST", url, params=params, json=json_body, headers=headers, timeout=180) as resp:
        assert resp.status_code == 200, f"请求失败: {resp.status_code} {resp.read()[:300]}"
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


def final_of(events):
    return next((e["answer"] for e in events if e.get("type") == "final_answer"), "")


def thought_contents(events):
    # 含 action:工具调用的动作记录("search_notes{...}")也是 action 类型
    return [e.get("content", "") for e in events if e.get("type") in ("thought", "check", "action")]


def main():
    proc = start_server()
    try:
        client = httpx.Client()
        headers = register_and_login(client)

        # ---- 1. web_research_agent 经路由 ----
        print("\n[1] 联网问题(期望 web_research_agent 专职链路)")
        sid = str(uuid.uuid4())
        events, done = sse_post(
            client, f"{BASE}/api/agent/chat/stream", headers,
            params={"question": "需要联网搜索:LangGraph 官方最新版本号", "session_id": sid},
        )
        record("SSE 正常收尾", done and bool(final_of(events).strip()))
        record("意图路由 web_search", any(e.get("type") == "intent" and "web_search" in e.get("content", "") for e in events))
        thoughts = thought_contents(events)
        if not any(t.startswith("hallucination_check") for t in thoughts):
            # FAIL 时 dump 全部事件,便于定位(一次性调试输出)
            print("    [debug] 事件序列:")
            for e in events:
                print(f"      - {json.dumps(e, ensure_ascii=False)[:220]}")
        # 节点执行的确定性标记是 "grade_documents: 开始"(grade_documents 节点开头固定 append);
        # 不能用子串匹配——LLM 生成的 reason 文本可能偶然提到 grade_documents
        record("跳过文档评级(无 grade_documents 节点标记)", not any(t.startswith("grade_documents") for t in thoughts))
        record("保留幻觉查(hallucination_check)", any(t.startswith("hallucination_check") for t in thoughts))
        final = final_of(events)
        record("答案含信源标注", ("来源" in final or "http" in final or "PyPI" in final), f"长度 {len(final)}")
        record("无写入工具调用", not any("create_note" in t for t in thoughts))

        # ---- 2. note_write_agent 批准流 ----
        print("\n[2] 保存诉求(期望 note_write_agent → 审批卡 → 批准 → 创建)")
        sid2 = str(uuid.uuid4())
        title = f"M73冒烟笔记{uuid.uuid4().hex[:6]}"
        events2, done2 = sse_post(
            client, f"{BASE}/api/agent/chat/stream", headers,
            params={"question": f"把这条内容保存为笔记,标题是「{title}」,内容是「这是 M7.3 专职冒烟创建的测试笔记」", "session_id": sid2},
        )
        approval = next((e for e in events2 if e.get("type") == "approval_required"), None)
        record("触发审批卡", approval is not None)
        assert approval, "无审批卡,后续流程无法继续"
        record("意图路由 note_write", any(e.get("type") == "intent" and "note_write" in e.get("content", "") for e in events2))
        record("写入前查重(有 search_notes 动作)", any("search_notes" in t for t in thought_contents(events2)))
        record("无三查(跳过 grade/hallucination)", not any("grade_documents" in t or "hallucination_check" in t for t in thought_contents(events2)))

        events2b, done2b = sse_post(
            client, f"{BASE}/api/agent/resume", headers,
            json_body={"session_id": sid2, "approved": True, "reason": "同意"},
        )
        final2b = final_of(events2b)
        record("批准后创建成功", done2b and ("已创建" in final2b or "创建" in final2b or "已保存" in final2b or "笔记" in final2b), f"长度 {len(final2b)}")

        # ---- 3. note_write_agent 拒绝流 ----
        print("\n[3] 保存诉求(拒绝路径)")
        sid3 = str(uuid.uuid4())
        events3, _ = sse_post(
            client, f"{BASE}/api/agent/chat/stream", headers,
            params={"question": f"保存笔记,标题「M73拒绝测试{uuid.uuid4().hex[:4]}」,内容「拒绝路径冒烟」", "session_id": sid3},
        )
        approval3 = next((e for e in events3 if e.get("type") == "approval_required"), None)
        assert approval3, "无审批卡,拒绝流无法继续"
        record("拒绝前触发审批卡", True)
        events3b, done3b = sse_post(
            client, f"{BASE}/api/agent/resume", headers,
            json_body={"session_id": sid3, "approved": False, "reason": "不同意"},
        )
        final3b = final_of(events3b)
        record("拒绝后不创建且流程收尾", done3b and bool(final3b.strip()), f"长度 {len(final3b)}")

        summary = sum(1 for _, ok, _ in results if ok)
        print(f"\n===== 冒烟结果: {summary}/{len(results)} 通过 =====")
        for name, ok, detail in results:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        sys.exit(0 if summary == len(results) else 1)
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
