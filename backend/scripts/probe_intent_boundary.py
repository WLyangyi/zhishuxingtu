"""M7-1 验证:intent_boundary_set.json 边界用例真实 LLM 路由准确率。

运行方式(backend 目录下):
  $env:DEBUG='true'; .venv\\Scripts\\python.exe scripts\\probe_intent_boundary.py [--rounds 3]

每条用例跑 N 轮(LLM 分类有随机性,单轮结论不可靠——q007 探针已证 2/5 误判率),
输出每条的分轮结果与总体准确率(按"多数票"与"全对率"两个口径)。
"""

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402  P11: 先缓存健康 pydantic

from app.services.agent.nodes import intent_classify  # noqa: E402

BOUNDARY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval", "intent_boundary_set.json"
)

parser = argparse.ArgumentParser()
parser.add_argument("--rounds", type=int, default=3)
args = parser.parse_args()

with open(BOUNDARY_PATH, encoding="utf-8") as f:
    cases = json.load(f)

print(f"边界用例 {len(cases)} 条 × {args.rounds} 轮\n")

majority_ok = 0
all_ok = 0
for case in cases:
    votes = []
    for _ in range(args.rounds):
        out = intent_classify({"question": case["question"], "thoughts": []})
        votes.append(out["intent"])
    counter = Counter(votes)
    majority = counter.most_common(1)[0][0]
    stable = all(v == case["expected_intent"] for v in votes)
    hit = majority == case["expected_intent"]
    majority_ok += hit
    all_ok += stable
    flag = "PASS" if stable else ("WEAK" if hit else "FAIL")
    print(
        f"[{flag}] {case['id']} 期望={case['expected_intent']} 实际={dict(counter)} | {case['note']}"
    )

total = len(cases)
print(f"\n多数票准确率: {majority_ok}/{total} = {majority_ok / total:.1%}")
print(f"全轮稳定率:   {all_ok}/{total} = {all_ok / total:.1%}")
sys.exit(0 if majority_ok == total else 1)
