# -*- coding: utf-8 -*-
"""
M2-1 校验:检查 eval_set_v1.json 的结构、分类配额、相关文档 id 是否真实存在。

用法:
    .venv\\Scripts\\python.exe scripts/validate_eval_set.py
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402

EXPECTED_COUNTS = {
    "simple_fact": 10,
    "single_doc": 10,
    "multi_hop": 10,
    "comparison": 10,
    "temporal": 5,
    "edge_case": 5,
}
REQUIRED_FIELDS = {"id", "question", "expected_answer", "relevant_doc_ids", "category"}


def main() -> int:
    path = settings.EVAL_SET_PATH
    if not os.path.exists(path):
        print(f"[失败] 找不到 eval set: {path}")
        return 1

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    errors = []
    seen_ids = set()
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"#{idx}: 条目不是对象")
            continue
        missing = REQUIRED_FIELDS - set(item.keys())
        if missing:
            errors.append(f"{item.get('id', idx)}: 缺字段 {sorted(missing)}")
        if item.get("id") in seen_ids:
            errors.append(f"{item.get('id')}: id 重复")
        seen_ids.add(item.get("id"))
        if item.get("category") not in EXPECTED_COUNTS:
            errors.append(f"{item.get('id')}: category '{item.get('category')}' 非法")
        if not isinstance(item.get("relevant_doc_ids"), list):
            errors.append(f"{item.get('id')}: relevant_doc_ids 应为数组")

    counts = Counter(item.get("category") for item in data if isinstance(item, dict))
    for cat, expected in EXPECTED_COUNTS.items():
        actual = counts.get(cat, 0)
        flag = "OK" if actual == expected else "MISMATCH"
        print(f"  {cat:14s} {actual:3d}/{expected}  {flag}")
        if actual != expected:
            errors.append(f"分类 {cat}: 期望 {expected} 实际 {actual}")

    # 相关文档 id 必须真实存在
    from app.db.session import SessionLocal
    from app.models.note import Note

    db = SessionLocal()
    try:
        existing = {row[0] for row in db.query(Note.id).all()}
    finally:
        db.close()

    for item in data:
        for did in item.get("relevant_doc_ids", []):
            if did not in existing:
                errors.append(f"{item.get('id')}: relevant_doc_id {did} 在 notes 表不存在")

    print(f"\n总条目: {len(data)}")
    if errors:
        print(f"[失败] {len(errors)} 个问题:")
        for e in errors:
            print("  -", e)
        return 1
    print("[通过] eval set 结构、配额、文档 id 全部有效")
    return 0


if __name__ == "__main__":
    sys.exit(main())
