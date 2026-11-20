# -*- coding: utf-8 -*-
"""阶段1b:偏航 eval + per-turn token 增量。

从 multi_turn_set.json 读 anchor_deviation 类偏航用例,多轮共享 thread 跑:
  1. 验证每轮答案含 expect_keywords(锚点不偏航到无关内容)
  2. 量每轮真实 token_used(per-turn 增量)
  3. --compare-shadow 额外跑 shadow 模式(只算不注入),对比锚点注入的 token 成本

用法:
    .venv\\Scripts\\python.exe eval/run_anchor_eval.py [--compare-shadow]
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 与 run_eval.py 一致的本机 workaround(WMI 卡死 + transformers 连带阻塞)
sys.modules.setdefault("transformers", None)
import platform as _platform  # noqa: E402

_platform.win32_ver = lambda *a, **k: ("", "", "", "")
_platform.machine = lambda: os.environ.get("PROCESSOR_ARCHITECTURE") or "AMD64"

from app.core.config import settings  # noqa: E402
from app.services import init_hybrid_search, init_vector_store  # noqa: E402

CASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "multi_turn_set.json")
REPORT_DIR = settings.EVAL_REPORT_DIR


def run_case(turns, user_id: str, thread_id: str, mode: str) -> list:
    """跑一条偏航用例的多轮,返回每轮结果(含关键词命中与 token)。

    mode: on=写 state+注入锚点 / shadow=只算不写不注入(量化锚点注入 token 成本)。
    通过改 nodes 模块的 CORE_INTENT_ENABLED 切换,节点函数运行时读取,无需重建图。
    """
    from app.services.agent.graph import build_input, get_graph
    from app.services.observability.langfuse_trace import build_stream_config
    from app.services.tools.context import ToolContext, set_tool_context
    import app.services.agent.nodes as nodes

    nodes.CORE_INTENT_ENABLED = mode

    set_tool_context(ToolContext(user_id=user_id, session_id="anchor-eval"))
    graph = get_graph()
    history: list = []
    turn_results: list = []
    for index, turn in enumerate(turns):
        input_data = build_input(
            turn["question"], session_id="anchor-eval", user_id=user_id, history=history
        )
        cfg = build_stream_config(thread_id)
        cfg["recursion_limit"] = 40
        answer = ""
        for step in graph.stream(input_data, config=cfg):
            for _, value in step.items():
                if value.get("answer"):
                    answer = value["answer"]
        state = graph.get_state({"configurable": {"thread_id": thread_id}}).values or {}
        # token_used 是本轮值(每轮 build_input 清零),直接取即为 per-turn 增量
        turn_tokens = int(state.get("token_used") or 0)
        keywords = turn.get("expect_keywords") or []
        hit = any(k in answer for k in keywords) if keywords else None
        turn_results.append(
            {
                "turn": index + 1,
                "question": turn["question"],
                "answer": answer[:200],
                "expect_keywords": keywords,
                "keyword_hit": hit,
                "turn_tokens": turn_tokens,
            }
        )
        history.append({"role": "user", "content": turn["question"]})
        history.append({"role": "assistant", "content": answer})
    return turn_results


def check_case(case: dict, turn_results: list) -> list:
    """验证每轮答案含 expect_keywords(锚定不偏航),返回失败原因列表。
    仅检查声明了关键词的轮次(首轮通常只定目标,无关键词)。"""
    fails: list = []
    for tr in turn_results:
        if tr["expect_keywords"] and not tr["keyword_hit"]:
            fails.append(f"turn{tr['turn']} 缺少锚点关键词:{'/'.join(tr['expect_keywords'])}")
    return fails


def write_report(results: list, shadow_results) -> str:
    os.makedirs(REPORT_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    total = len(results)
    passed = sum(1 for r in results if not r["fails"])
    lines = [
        f"# 偏航 eval 报告({today})",
        "",
        f"> 偏航用例 {total} 条,多轮共享 thread 跑,验证每轮答案含 expect_keywords(锚点不偏航)。",
        "",
        "## 偏航用例结果",
        "",
        "| id | 判定 | 失败原因 | 各轮关键词命中 |",
        "|---|---|---|---|",
    ]
    for r in results:
        hits = " / ".join("命中" if t["keyword_hit"] else "未命中" for t in r["turns"])
        lines.append(
            f"| {r['id']} | {'通过' if not r['fails'] else '未通过'} | "
            f"{'；'.join(r['fails']) or '—'} | {hits} |"
        )
    lines += ["", f"通过率:{passed}/{total} = {passed / total:.1%}" if total else "", ""]

    lines += [
        "## 每轮 token 增量(on 模式)",
        "",
        "| id | 轮 | 问题 | turn_tokens |",
        "|---|---|---|---|",
    ]
    for r in results:
        for t in r["turns"]:
            lines.append(f"| {r['id']} | {t['turn']} | {t['question'][:24]} | {t['turn_tokens']} |")

    if shadow_results:
        lines += [
            "",
            "## 锚点注入 token 增量(on − shadow)",
            "",
            "| id | 轮 | on | shadow | 增量 |",
            "|---|---|---|---|---|",
        ]
        for r, s in zip(results, shadow_results):
            for t, st in zip(r["turns"], s["turns"]):
                delta = t["turn_tokens"] - st["turn_tokens"]
                lines.append(
                    f"| {r['id']} | {t['turn']} | {t['turn_tokens']} | {st['turn_tokens']} | {delta} |"
                )
        n_on = sum(len(r["turns"]) for r in results)
        n_sh = sum(len(r["turns"]) for r in shadow_results)
        avg_on = sum(t["turn_tokens"] for r in results for t in r["turns"]) / n_on if n_on else 0
        avg_sh = sum(t["turn_tokens"] for r in shadow_results for t in r["turns"]) / n_sh if n_sh else 0
        lines += [
            "",
            f"平均: on {avg_on:.0f} / shadow {avg_sh:.0f} / 锚点增量 {avg_on - avg_sh:.0f} token/轮",
        ]

    md_path = os.path.join(REPORT_DIR, f"{today}-anchor-eval.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--compare-shadow", action="store_true",
        help="额外跑 shadow 模式对比锚点注入的 token 增量",
    )
    args = parser.parse_args()

    init_vector_store(settings.FAISS_INDEX_PATH)
    init_hybrid_search()

    with open(CASE_PATH, encoding="utf-8") as f:
        cases = [c for c in json.load(f) if c.get("category") == "anchor_deviation"]
    if not cases:
        print("[失败] 没有偏航用例")
        return 1

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

    results: list = []
    for case in cases:
        print(f"[anchor] {case['id']} {case.get('note', '')} ...", flush=True)
        thread_id = f"anchor-{case['id']}-{int(time.time() * 1000)}"
        try:
            turns = run_case(case["turns"], uid, thread_id, "on")
            fails = check_case(case, turns)
        except Exception as e:  # noqa: BLE001 单条异常不拖垮整轮
            turns = []
            fails = [f"运行异常:{type(e).__name__}"]
        results.append({"id": case["id"], "note": case.get("note", ""), "turns": turns, "fails": fails})
        print(f"    {'通过' if not fails else '未通过:' + '；'.join(fails)}", flush=True)

    shadow_results = []
    if args.compare_shadow:
        print("\n[anchor] === shadow 对比 ===", flush=True)
        for case in cases:
            thread_id = f"anchor-sh-{case['id']}-{int(time.time() * 1000)}"
            try:
                turns = run_case(case["turns"], uid, thread_id, "shadow")
            except Exception as e:  # noqa: BLE001
                turns = []
            shadow_results.append({"id": case["id"], "turns": turns})
            print(f"  {case['id']} shadow 完成", flush=True)

    path = write_report(results, shadow_results if args.compare_shadow else None)
    print(f"\n[报告已写入] {path}")
    passed = sum(1 for r in results if not r["fails"])
    print(f"偏航用例:{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
