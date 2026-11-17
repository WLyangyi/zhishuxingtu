"""端到端验证（为 Agent 架构文档做交叉验证）。

跑 2 个用例：
  A. 闲聊"你好" → 期望 chat_agent → direct_answer（无工具事件）
  B. 知识问题 → 期望 knowledge_agent → search_notes → agent_step 循环 → 三查 → final_answer

每个用例独立 session，SSE 事件全部落 JSON 供文档引用。

用法（已登录服务在 127.0.0.1:8765）：
  .venv/Scripts/python.exe scripts/verify_agent_arch_for_doc.py
"""

import json
import os
import sys
import time
import uuid

import httpx

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

BASE = "http://127.0.0.1:8765"
USERNAME = "m7smoke_9c2b8170"  # 项目自带 smoke 账号
PASSWORD = "M7Smoke#2026"


def login() -> dict:
    r = httpx.post(
        f"{BASE}/api/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
        timeout=30,
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def stream_chat(headers: dict, question: str, session_id: str, tag: str) -> tuple[list[dict], bool]:
    events: list[dict] = []
    done = False
    with httpx.stream(
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


def summarize(events: list[dict]) -> dict:
    types = [e.get("type") for e in events if isinstance(e, dict)]
    thought_count = types.count("thought")
    final_answer_events = [e for e in events if isinstance(e, dict) and e.get("type") == "final_answer"]
    approval_events = [e for e in events if isinstance(e, dict) and e.get("type") == "approval_required"]
    usage_events = [e for e in events if isinstance(e, dict) and e.get("type") in ("usage", "budget")]
    agent_route_events = [
        e for e in events if isinstance(e, dict) and e.get("type") in ("agent_route", "routing", "intent")
    ]
    final_answer = ""
    for ev in final_answer_events:
        if isinstance(ev.get("content"), str):
            final_answer = ev["content"]
            break
        if isinstance(ev.get("answer"), str):
            final_answer = ev["answer"]
            break
    return {
        "event_count": len(events),
        "event_types": types,
        "thought_count": thought_count,
        "has_final_answer": bool(final_answer_events),
        "final_answer_preview": final_answer[:200],
        "has_approval": bool(approval_events),
        "usage_events": usage_events,
        "agent_routing_events": agent_route_events[:5],
    }


def main() -> int:
    print(f"# 端到端验证 → {BASE}")
    headers = login()
    print(f"登录 OK (user={USERNAME})")

    cases = [
        {
            "tag": "A-直接问答",
            "question": "你好，请做个自我介绍",
            "session_id": str(uuid.uuid4()),
        },
        {
            "tag": "B-知识检索",
            "question": "Agentic RAG 架构里有几个子 Agent？分别是？",
            "session_id": str(uuid.uuid4()),
        },
    ]

    output = {"base": BASE, "user": USERNAME, "cases": []}
    for case in cases:
        print(f"\n=== 用例 {case['tag']} ===")
        print(f"问题: {case['question']}")
        print(f"session_id: {case['session_id']}")
        t0 = time.time()
        events, done = stream_chat(headers, case["question"], case["session_id"], case["tag"])
        elapsed = time.time() - t0
        summary = summarize(events)
        summary["latency_sec"] = round(elapsed, 2)
        summary["done_flag"] = done
        print(f"完成: 事件 {summary['event_count']} 个, 耗时 {summary['latency_sec']}s, done= {done}")
        print(f"  事件类型分布: {summary['event_types']}")
        if summary["final_answer_preview"]:
            print(f"  答案预览: {summary['final_answer_preview']}")
        if summary["usage_events"]:
            print(f"  usage 事件: {summary['usage_events'][:2]}")

        case_out = {
            "tag": case["tag"],
            "question": case["question"],
            "session_id": case["session_id"],
            "summary": summary,
            "events": events,
        }
        output["cases"].append(case_out)

    out_path = os.path.join(BACKEND_DIR, "data", "agent_doc_verify.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n完整事件已保存: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
