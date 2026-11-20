# -*- coding: utf-8 -*-
"""阶段1b:路由回归硬门禁。

整合两套路由准确率,作为一期上线硬门禁:
  1. 14 条意图边界用例(intent_boundary_set.json):每条跑 3 轮取多数票,容差 LLM 抖动
  2. 50 条 eval(run_eval 产出的 *-comparison.json 摘要):routing_accuracy

退出码:0 = 全过,1 = 任一未达标(可直接用于 CI 阻断)。

用法:
    .venv\\Scripts\\python.exe eval/eval_route_gate.py [--rounds 3]
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 与 run_eval.py 一致的本机 workaround
sys.modules.setdefault("transformers", None)
import platform as _platform  # noqa: E402

_platform.win32_ver = lambda *a, **k: ("", "", "", "")
_platform.machine = lambda: os.environ.get("PROCESSOR_ARCHITECTURE") or "AMD64"

from app.services.agent.nodes import intent_classify  # noqa: E402

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
BOUNDARY_PATH = os.path.join(EVAL_DIR, "intent_boundary_set.json")
REPORT_DIR = os.path.join(EVAL_DIR, "reports")

# 阈值:非已知局限用例全对(已知局限为 WRITE_KEYWORDS 兜底设计取舍,单独报告不纳入门禁);
# 50 条 eval 沿用 eval_gate 口径
BOUNDARY_THRESHOLD = 1.0
EVAL_ROUTING_THRESHOLD = 0.90


def majority_vote(votes):
    """多数票:取出现次数最多的意图,平票取首个。"""
    if not votes:
        return ""
    return Counter(votes).most_common(1)[0][0]


def evaluate_gate(boundary_acc, eval_routing_acc):
    """门禁判定纯函数:返回 (passed, failed列表)。无数据视为不通过。"""
    failed = []
    if boundary_acc < BOUNDARY_THRESHOLD:
        failed.append(f"boundary_accuracy={boundary_acc:.3f}<{BOUNDARY_THRESHOLD:.3f}")
    if eval_routing_acc is None:
        failed.append("eval_routing_accuracy 无数据(未找到 *-comparison.json)")
    elif eval_routing_acc < EVAL_ROUTING_THRESHOLD:
        failed.append(f"eval_routing_accuracy={eval_routing_acc:.3f}<{EVAL_ROUTING_THRESHOLD:.2f}")
    return not failed, failed


def run_boundary(cases, rounds):
    """边界用例跑多轮取多数票。已知局限用例(WRITE_KEYWORDS 兜底设计取舍)单独报告,
    不纳入门禁阈值。返回 (非已知局限命中率, details)。"""
    strict_hits = 0
    strict_total = 0
    details = []
    for case in cases:
        votes = []
        for _ in range(rounds):
            out = intent_classify({"question": case["question"], "thoughts": []})
            votes.append(out["intent"])
        majority = majority_vote(votes)
        hit = majority == case["expected_intent"]
        known = bool(case.get("known_limitation"))
        if not known:
            strict_total += 1
            strict_hits += hit
        details.append(
            {
                "id": case["id"],
                "expected": case["expected_intent"],
                "votes": dict(Counter(votes)),
                "majority": majority,
                "hit": hit,
                "known_limitation": known,
                "note": case.get("note", ""),
            }
        )
    strict_acc = strict_hits / strict_total if strict_total else 1.0
    return strict_acc, details


def latest_eval_summary():
    paths = glob.glob(os.path.join(REPORT_DIR, "*-comparison.json"))
    if not paths:
        return None
    return max(paths, key=os.path.getmtime)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()

    with open(BOUNDARY_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    boundary_acc, boundary_details = run_boundary(cases, args.rounds)

    eval_path = latest_eval_summary()
    eval_routing_acc = None
    eval_detail = None
    if eval_path:
        with open(eval_path, encoding="utf-8") as f:
            summary = json.load(f)
        eval_routing_acc = summary.get("routing_accuracy")
        eval_detail = {
            "summary": eval_path,
            "count": summary.get("count"),
            "routing_accuracy": eval_routing_acc,
        }

    passed, failed = evaluate_gate(boundary_acc, eval_routing_acc)
    gate = {
        "boundary_accuracy": round(boundary_acc, 4),
        "boundary_threshold": round(BOUNDARY_THRESHOLD, 4),
        "boundary_details": boundary_details,
        "eval_routing_accuracy": eval_routing_acc,
        "eval_routing_threshold": EVAL_ROUTING_THRESHOLD,
        "eval_detail": eval_detail,
        "passed": passed,
        "failed": failed,
    }
    gate_path = os.path.join(REPORT_DIR, "route-gate.json")
    with open(gate_path, "w", encoding="utf-8") as f:
        json.dump(gate, f, ensure_ascii=False, indent=2)

    print(f"边界用例(非已知局限):{boundary_acc:.1%} (阈值 {BOUNDARY_THRESHOLD:.0%})")
    for d in boundary_details:
        if d["known_limitation"]:
            flag = "LIMIT"
        elif d["hit"]:
            flag = "PASS"
        else:
            flag = "FAIL"
        print(f"  [{flag}] {d['id']} 期望={d['expected']} 实际={d['votes']}")
    if eval_routing_acc is not None:
        print(f"eval 路由:{eval_routing_acc:.1%} (阈值 {EVAL_ROUTING_THRESHOLD:.0%})")
    else:
        print("eval 路由:无数据(未找到 *-comparison.json)")
    print(f"\n[门禁 {'通过' if passed else '未通过'}] {'、'.join(failed) if failed else '全部达标'}")
    print(f"门禁 JSON: {gate_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
