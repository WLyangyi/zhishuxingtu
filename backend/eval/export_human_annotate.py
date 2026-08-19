# -*- coding: utf-8 -*-
"""
M2-5 人工校准:按分类均匀抽 10 条,重跑 agent 生成答案 + 裁判打分,输出人工标注模板。

用法:
    .venv\\Scripts\\python.exe eval/export_human_annotate.py
"""
import json
import os
import random
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402  P11
from app.services import init_hybrid_search, init_vector_store  # noqa: E402

SAMPLE = {
    "simple_fact": 2,
    "single_doc": 2,
    "multi_hop": 2,
    "comparison": 2,
    "temporal": 1,
    "edge_case": 1,
}


def sample_items(data):
    random.seed(42)
    by_cat = {}
    for it in data:
        by_cat.setdefault(it["category"], []).append(it)
    picked = []
    for cat, n in SAMPLE.items():
        pool = by_cat.get(cat, [])
        picked.extend(random.sample(pool, min(n, len(pool))))
    return picked


def main() -> int:
    if not os.path.exists(settings.EVAL_SET_PATH):
        print(f"[失败] 找不到 eval set: {settings.EVAL_SET_PATH}")
        return 1

    init_vector_store(settings.FAISS_INDEX_PATH)
    init_hybrid_search()

    with open(settings.EVAL_SET_PATH, encoding="utf-8") as f:
        data = json.load(f)
    items = sample_items(data)

    from app.db.session import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("[失败] 无用户")
            return 1
    finally:
        db.close()

    from app.services.llm.judge_metrics import judge_answer_relevancy, judge_faithfulness
    from eval.run_eval import get_full_sources, run_agent

    rows = []
    for i, it in enumerate(items, 1):
        print(f"[{i}/{len(items)}] {it['id']} 生成 agent 答案...")
        a_ids, answer, _ = run_agent(it["question"], user.id)
        db = SessionLocal()
        try:
            a_full = get_full_sources(a_ids, db)
        finally:
            db.close()
        f = judge_faithfulness(it["question"], answer, a_full) if answer else {"score": None}
        r = judge_answer_relevancy(it["question"], answer) if answer else {"score": None}
        rows.append({
            "id": it["id"],
            "category": it["category"],
            "question": it["question"],
            "answer": answer or "",
            "judge_faith": f["score"],
            "judge_rel": r["score"],
        })

    report_path = os.path.join(settings.EVAL_REPORT_DIR, f"{datetime.now().strftime('%Y-%m-%d')}-human-annotate.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    def fmt(x):
        return "—" if x is None else f"{x:.2f}"

    lines = [
        "# 人工校准标注表",
        "",
        "请对照下方**完整答案**打分(0-1):`human_faith`=答案是否有检索出处,`human_rel`=是否回应了问题。",
        "",
        "## 打分表",
        "",
        "| id | 分类 | 问题 | judge_faith | judge_rel | human_faith | human_rel |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        q = r["question"][:60].replace("|", "\\|")
        lines.append(
            f"| {r['id']} | {r['category']} | {q} | {fmt(r['judge_faith'])} | "
            f"{fmt(r['judge_rel'])} |  |  |"
        )
    lines += ["", "## 完整答案", ""]
    for r in rows:
        lines.append(f"### {r['id']}（{r['category']}）：{r['question']}")
        lines.append("")
        lines.append((r["answer"] or "（无答案）").replace("\n", "\n\n"))
        lines.append("")
    lines.append("")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[标注文件已写入] {report_path} (请填 human_faith / human_rel 两列)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
