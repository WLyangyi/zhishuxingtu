# -*- coding: utf-8 -*-
"""Phase 2:Agent 行为评测。

与 run_eval.py 的区别:
  run_eval.py 看"答得好不好"(retrieval / 裁判分数)
  本脚本看"行为对不对":该说没有的有没有乱编、该拒的有没有拒、该停的有没有停

用法:
    .venv\\Scripts\\python.exe eval/run_behavior_eval.py [--ids b001,b003]
"""
import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 与 run_eval.py 一致的环境 workaround(本机 WMI 查询卡死 + transformers 连带阻塞)
sys.modules.setdefault("transformers", None)
import platform as _platform  # noqa: E402

_platform.win32_ver = lambda *a, **k: ("", "", "", "")
_platform.machine = lambda: os.environ.get("PROCESSOR_ARCHITECTURE") or "AMD64"

from app.core.config import settings  # noqa: E402
from app.services import init_hybrid_search, init_vector_store  # noqa: E402

SET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "behavior_eval_set.json")
REPORT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "reports",
    f"{datetime.now().strftime('%Y-%m-%d')}-behavior.md",
)


def run_turns(turns: List[str], user_id: str, thread_id: str) -> Dict[str, Any]:
    """按会话跑一轮或多轮,返回最终答案 + 意图 + 工具调用日志 + token + 延迟。"""
    from app.services.agent.graph import build_input, get_graph
    from app.services.observability.langfuse_trace import build_stream_config
    from app.services.tools.context import ToolContext, set_tool_context

    set_tool_context(ToolContext(user_id=user_id, session_id="behavior-eval"))
    graph = get_graph()
    history: List[dict] = []
    answer = ""
    started = time.perf_counter()
    for question in turns:
        input_data = build_input(question, session_id="behavior-eval", user_id=user_id, history=history)
        cfg = build_stream_config(thread_id)
        # 行为用例里可能出现"检索被熔断→再换词"的循环,给足超步数,避免直接抛 GraphRecursionError 中断整轮评测
        cfg["recursion_limit"] = 40
        for step in graph.stream(input_data, config=cfg):
            for _, v in step.items():
                if v.get("answer"):
                    answer = v["answer"]
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
    latency_ms = int((time.perf_counter() - started) * 1000)

    state = graph.get_state({"configurable": {"thread_id": thread_id}}).values or {}
    return {
        "answer": answer,
        "intent": state.get("intent") or "knowledge",
        "tool_log": state.get("tool_calls_log") or [],
        "token_used": state.get("token_used") or 0,
        "latency_ms": latency_ms,
    }


def check(item: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
    """按用例声明的断言逐条检查,返回失败原因列表(空 = 通过)。"""
    checks = item.get("checks") or {}
    answer = result["answer"] or ""
    tools = [t.get("tool") for t in result["tool_log"]]
    fails: List[str] = []

    if "require_any_phrases" in checks:
        if not any(p.lower() in answer.lower() for p in checks["require_any_phrases"]):
            fails.append("缺少预期表述")
    if "forbid_phrases" in checks:
        hit = [p for p in checks["forbid_phrases"] if p.lower() in answer.lower()]
        if hit:
            fails.append("出现禁止内容:" + ",".join(hit))
    if "forbid_tools" in checks:
        hit = sorted(set(tools) & set(checks["forbid_tools"]))
        if hit:
            fails.append("调用了禁止工具:" + ",".join(hit))
    if "require_min_tool_calls" in checks and len(tools) < checks["require_min_tool_calls"]:
        fails.append(f"工具调用过少({len(tools)})")
    if "max_tool_calls" in checks and len(tools) > checks["max_tool_calls"]:
        fails.append(f"工具调用超限({len(tools)}>{checks['max_tool_calls']})")
    if "max_search_calls" in checks:
        n = sum(
            1
            for t in result["tool_log"]
            if t.get("tool") == "search_notes" and t.get("status") == "success"
        )
        if n > checks["max_search_calls"]:
            fails.append(f"重复检索未熔断({n}次)")
    if checks.get("require_no_error_answer"):
        if not answer.strip() or "工具执行出错" in answer:
            fails.append("答案为空或暴露工具错误")
    return fails


def _tool_chain(tool_log: List[dict]) -> str:
    """把工具调用压成一行,便于在报告里看出"检索了几次、被拦了几次"。"""
    if not tool_log:
        return "—"
    parts = [
        f"{t.get('tool')}{'✓' if t.get('status') == 'success' else '✗'}" for t in tool_log
    ]
    return " → ".join(parts)


def write_report(results: List[dict]) -> None:
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    lines = [
        "# Agent 行为评测报告",
        "",
        f"生成时间:{datetime.now().strftime('%Y-%m-%d %H:%M')}  用例数:{total}",
        f"通过率:{passed}/{total} = {passed / total:.1%}" if total else "通过率:—",
        "",
        "## 分类通过率",
        "",
        "| 分类 | 通过/总数 |",
        "|---|---|",
    ]
    by_cat = Counter()
    for r in results:
        by_cat[(r["category"], r["ok"])] += 1
    cats = sorted({r["category"] for r in results})
    for cat in cats:
        p, f = by_cat.get((cat, True), 0), by_cat.get((cat, False), 0)
        lines.append(f"| {cat} | {p}/{p + f} |")
    lines += ["", "## 逐条结果", "", "| id | 分类 | 判定 | 失败原因 | 意图 | 工具链 | 延迟 ms |", "|---|---|---|---|---|---|---|"]
    for r in results:
        lines.append(
            f"| {r['id']} | {r['category']} | {'通过' if r['ok'] else '未通过'} | "
            f"{'；'.join(r['fails']) or '—'} | {r['intent']} | {r['tool_chain']} | {r['latency_ms']} |"
        )
    lines += ["", "## 答案摘录", ""]
    for r in results:
        lines += [f"### {r['id']} {r['question']}", "", r["answer"].strip()[:400] or "(空)", ""]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[报告已写入] {REPORT_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", default="", help="只跑指定 id,逗号分隔")
    args = parser.parse_args()

    with open(SET_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",") if x.strip()}
        data = [d for d in data if d["id"] in wanted]
    if not data:
        print("[失败] 没有可跑的用例")
        return 1

    init_vector_store(settings.FAISS_INDEX_PATH)
    init_hybrid_search()

    from app.db.session import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("[失败] 无用户")
            return 1
        uid = user.id
    finally:
        db.close()

    results: List[dict] = []
    for i, item in enumerate(data, 1):
        turns = item.get("turns") or [item["question"]]
        print(f"[{i}/{len(data)}] {item['id']} {item['category']} {turns[0][:30]} ...", flush=True)
        thread_id = f"behavior-{item['id']}-{int(time.time() * 1000)}"
        try:
            result = run_turns(turns, uid, thread_id)
            fails = check(item, result)
        except Exception as e:  # noqa: BLE001  单条异常不拖垮整轮评测
            result = {"answer": "", "intent": "-", "tool_log": [], "token_used": 0, "latency_ms": 0}
            fails = [f"运行异常:{type(e).__name__}"]
        results.append({**result, "id": item["id"], "category": item["category"],
                        "question": " -> ".join(turns), "ok": not fails, "fails": fails,
                        "tool_chain": _tool_chain(result["tool_log"])})
        print(f"    {'通过' if not fails else '未通过:' + '；'.join(fails)}", flush=True)

    write_report(results)
    print(f"完成: 共 {len(results)} 条,通过 {sum(1 for r in results if r['ok'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
