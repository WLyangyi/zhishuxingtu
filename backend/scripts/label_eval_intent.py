"""M7-1 一次性脚本:给 eval_set_v1.json 全部 50 条标注 expected_intent=knowledge。

依据:M6/M7 评测集设计上全部为知识库检索类问题(6 类配额均为 KB 内容),
M6 全量运行收集到的 1 条 web_search 即误分类佐证(评测集没有实时信息类问题)。
"""

import json
import os

EVAL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval", "eval_set_v1.json"
)

with open(EVAL_PATH, encoding="utf-8") as f:
    items = json.load(f)

for item in items:
    item["expected_intent"] = "knowledge"

with open(EVAL_PATH, "w", encoding="utf-8", newline="\n") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"已标注 {len(items)} 条 expected_intent=knowledge -> {EVAL_PATH}")
