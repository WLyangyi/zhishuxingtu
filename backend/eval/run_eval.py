# -*- coding: utf-8 -*-
"""
M2-4 评估脚本:旧基线(baseline RAG) vs 新 agent(ReAct) 跑 eval set,输出对比报告。

指标:
  recall@k       确定性,纯计算(相关文档在检索 top-k 里的覆盖率)
  faithfulness   qwen3.7-max 裁判,答案声明是否 grounded 于检索证据
  answer_relevancy qwen3.7-max 裁判,答案是否回应问题

用法:
    .venv\\Scripts\\python.exe eval/run_eval.py [--limit N] [--skip-judge] [--agent-version agent-v1]
"""
import argparse
import json
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402  P11: 先缓存健康 pydantic
from app.services import init_hybrid_search, init_vector_store  # noqa: E402

TOP_K = 5  # 与 /api/search/ai 一致


def recall_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> Optional[float]:
    """相关文档在前 k 检索结果中的覆盖率。无相关文档(edge_case)返回 None。"""
    if not relevant_ids:
        return None
    hit = set(retrieved_ids[:k]) & set(relevant_ids)
    return len(hit) / len(relevant_ids)


def run_baseline(question: str, db):
    """旧基线: 与 /api/search/ai 同链路(hybrid_search_notes + rag_chain.invoke_with_custom_context)。
    M7.2 起附带延迟测量(ms),供报告聚合 mean/P95。"""
    from app.api.routes.search import hybrid_search_notes
    from app.services.rag_chain import get_rag_chain

    started = time.perf_counter()
    notes = hybrid_search_notes(question, db, k=TOP_K, use_reranker=True)
    retrieved_ids = [n.id for n, _ in notes]
    result = get_rag_chain().invoke_with_custom_context(question, notes)
    latency_ms = int((time.perf_counter() - started) * 1000)
    sources = [
        {"id": n.id, "title": n.title, "content": (n.content or "")[:2000]}
        for n, _ in notes
    ]
    return retrieved_ids, result["answer"] or "", sources, latency_ms


def run_agent(question: str, user_id: str):
    """新链路: graph.stream, 收集 final answer + 检索到的 documents + 意图 + 工具调用数 + 延迟(ms)。"""
    from app.services.agent.graph import build_input, get_graph
    from app.services.observability.langfuse_trace import build_stream_config
    from app.services.tools.context import ToolContext, set_tool_context

    set_tool_context(ToolContext(user_id=user_id, session_id="eval-sess"))
    graph = get_graph()
    thread_id = f"eval-{int(time.time() * 1000)}"
    input_data = build_input(question, session_id="eval-sess", user_id=user_id)

    final_answer = ""
    documents: List[dict] = []
    tool_calls = 0
    seen: set = set()
    started = time.perf_counter()
    for step in graph.stream(input_data, config=build_stream_config(thread_id)):
        for _, v in step.items():
            if v.get("answer"):
                final_answer = v["answer"]
            tool_calls = max(tool_calls, len(v.get("tool_calls_log") or []))
            for d in v.get("documents") or []:
                did = d.get("id")
                if did and did not in seen:
                    seen.add(did)
                    documents.append(d)
    latency_ms = int((time.perf_counter() - started) * 1000)

    config = {"configurable": {"thread_id": thread_id}}
    state_values = graph.get_state(config).values or {}
    intent = state_values.get("intent") or "knowledge"
    token_used = state_values.get("token_used") or 0
    retrieved_ids = [d["id"] for d in documents]
    return retrieved_ids, final_answer or "", documents, intent, tool_calls, latency_ms, token_used


def get_full_sources(note_ids: List[str], db) -> List[dict]:
    """按笔记 id 从 DB 取完整内容(≤2000字)。agent 侧 faithfulness 裁判用完整内容而非 snippet,
    避免因工具返回 snippet 过短导致"证据不足"误判(实测 snippet→0.0, 完整→1.0)。"""
    from app.models.note import Note
    if not note_ids:
        return []
    notes = db.query(Note).filter(Note.id.in_(note_ids)).all()
    return [{"id": n.id, "title": n.title, "content": (n.content or "")[:2000]} for n in notes]


def aggregate(results: List[dict]) -> Dict[str, Any]:
    def avg_metric(key: str) -> Optional[float]:
        vals = [r[key] for r in results if r.get(key) is not None]
        return round(mean(vals), 3) if vals else None

    total = {
        "count": len(results),
        "recall": avg_metric("recall"),
        "faithfulness": avg_metric("faithfulness"),
        "relevancy": avg_metric("relevancy"),
    }
    by_cat: Dict[str, Dict[str, Any]] = {}
    for item in results:
        cat = item["category"]
        bucket = by_cat.setdefault(cat, {"count": 0, "recall": [], "faithfulness": [], "relevancy": []})
        bucket["count"] += 1
        if item.get("recall") is not None:
            bucket["recall"].append(item["recall"])
        if item.get("faithfulness") is not None:
            bucket["faithfulness"].append(item["faithfulness"])
        if item.get("relevancy") is not None:
            bucket["relevancy"].append(item["relevancy"])
    return {"total": total, "by_category": by_cat}


def write_report(report_path: str, version: str, results: List[dict], agg_b: dict, agg_a: dict) -> None:
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    lines = [
        f"# Agentic RAG 对比报告({version})",
        "",
        f"生成时间:{datetime.now().strftime('%Y-%m-%d %H:%M')}  评测条数:{len(results)}",
        "",
        "## 总体指标",
        "",
        "| 指标 | 旧基线 baseline | 新 agent |",
        "|---|---|---|",
    ]

    def fmt(x):
        return "—" if x is None else f"{x:.3f}"

    for label, key in (("recall@k", "recall"), ("faithfulness", "faithfulness"), ("answer_relevancy", "relevancy")):
        lines.append(f"| {label} | {fmt(agg_b['total'].get(key))} | {fmt(agg_a['total'].get(key))} |")

    lines += ["", "## 按分类分桶", "", "| 分类 | 条数 | recall(b/a) | faithful(b/a) | relevancy(b/a) |", "|---|---|---|---|---|"]
    cats = sorted(set(r["category"] for r in results))
    for cat in cats:
        b, a = agg_b["by_category"][cat], agg_a["by_category"][cat]
        mean_b = lambda key: mean(b[key]) if b[key] else None
        mean_a = lambda key: mean(a[key]) if a[key] else None
        lines.append(
            f"| {cat} | {b['count']} | {fmt(mean_b('recall'))}/{fmt(mean_a('recall'))} | "
            f"{fmt(mean_b('faithfulness'))}/{fmt(mean_a('faithfulness'))} | "
            f"{fmt(mean_b('relevancy'))}/{fmt(mean_a('relevancy'))} |"
        )

    lines += [
        "",
        "## Agent 意图分布与成本",
        "",
        f"- 意图分布: {dict(Counter(r['agent'].get('intent') for r in results))}",
        f"- agent 平均工具调用次数: {mean([r['agent'].get('tool_calls') or 0 for r in results]):.2f}",
        f"- agent 平均 token 消耗: {mean([r['agent'].get('token_used') or 0 for r in results]):.0f}",
        "",
    ]

    def p95(vals: List[int]) -> Optional[int]:
        if not vals:
            return None
        s = sorted(vals)
        return s[max(0, math.ceil(0.95 * len(s)) - 1)]

    def ms(x):
        return "—" if x is None else f"{x}"

    b_lat = [r["baseline"].get("latency_ms") for r in results if r["baseline"].get("latency_ms") is not None]
    a_lat = [r["agent"].get("latency_ms") for r in results if r["agent"].get("latency_ms") is not None]
    lines += [
        "## 延迟(M7.2 口径,graph.stream 端到端)",
        "",
        "| 链路 | 均值 ms | P95 ms |",
        "|---|---|---|",
        f"| baseline | {ms(round(mean(b_lat))) if b_lat else '—'} | {ms(p95(b_lat))} |",
        f"| agent | {ms(round(mean(a_lat))) if a_lat else '—'} | {ms(p95(a_lat))} |",
        "",
    ]

    # 路由准确率(eval set 有 expected_intent 时输出)
    routed = [r for r in results if r["agent"].get("expected_intent")]
    if routed:
        hits = sum(1 for r in routed if r["agent"].get("intent") == r["agent"]["expected_intent"])
        lines += [f"- 路由准确率(vs expected_intent): {hits}/{len(routed)} = {hits / len(routed):.1%}", ""]

    lines += ["", "## 逐条明细", "", "| id | 分类 | recall(b/a) | faithful(b/a) | relevancy(b/a) | 问题 |", "|---|---|---|---|---|---|"]
    for r in results:
        b, a = r["baseline"], r["agent"]
        lines.append(
            f"| {r['id']} | {r['category']} | {fmt(b.get('recall'))}/{fmt(a.get('recall'))} | "
            f"{fmt(b.get('faithfulness'))}/{fmt(a.get('faithfulness'))} | "
            f"{fmt(b.get('relevancy'))}/{fmt(a.get('relevancy'))} | {r['question'][:40]} |"
        )
    lines.append("")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[报告已写入] {report_path}")


def write_eval_runs(db, results: List[dict], agent_version: str) -> None:
    from app.models.eval import EvalSet, EvalRun

    existing = {s.eval_id: s for s in db.query(EvalSet).all()}
    for item in results:
        es = existing.get(item["id"])
        if not es:
            es = EvalSet(
                eval_id=item["id"],
                question=item["question"],
                expected_answer=item.get("expected_answer", ""),
                relevant_doc_ids=json.dumps(item.get("rel_ids", []), ensure_ascii=False),
                category=item["category"],
            )
            db.add(es)
            existing[item["id"]] = es
    db.commit()

    for item in results:
        es = existing[item["id"]]
        for label, key in (("baseline", "baseline"), (agent_version, "agent")):
            m = item[key]
            db.add(EvalRun(
                eval_set_id=es.id,
                agent_version=label,
                metrics_json=json.dumps(
                    {"recall@k": m.get("recall"), "faithfulness": m.get("faithfulness"),
                     "answer_relevancy": m.get("relevancy"), "latency_ms": m.get("latency_ms"),
                     "intent": m.get("intent"), "tool_calls": m.get("tool_calls"),
                     "token_used": m.get("token_used")},
                    ensure_ascii=False,
                ),
            ))
    db.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 条(调试用)")
    parser.add_argument("--skip-judge", action="store_true", help="跳过裁判打分,只算 recall(省 token)")
    parser.add_argument("--agent-version", default="agent-v1")
    args = parser.parse_args()

    if not os.path.exists(settings.EVAL_SET_PATH):
        print(f"[失败] 找不到 eval set: {settings.EVAL_SET_PATH}")
        return 1

    if not args.skip_judge:
        from app.services.llm.judge_metrics import judge_faithfulness, judge_answer_relevancy
    else:
        judge_faithfulness = judge_answer_relevancy = None

    init_vector_store(settings.FAISS_INDEX_PATH)
    init_hybrid_search()

    with open(settings.EVAL_SET_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if args.limit:
        data = data[: args.limit]

    from app.db.session import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("[失败] 无用户")
            return 1
        uid = user.id

        results = []
        for i, item in enumerate(data, 1):
            qid, question = item["id"], item["question"]
            rel_ids = item.get("relevant_doc_ids") or []
            print(f"[{i}/{len(data)}] {qid} {question[:30]} ...")

            b_ids, b_answer, b_sources, b_latency = run_baseline(question, db)
            (
                a_ids, a_answer, a_sources,
                a_intent, a_tool_calls, a_latency, a_tokens,
            ) = run_agent(question, uid)

            row = {
                "id": qid,
                "category": item["category"],
                "question": question,
                "expected_answer": item.get("expected_answer", ""),
                "rel_ids": rel_ids,
                "baseline": {
                    "recall": recall_at_k(b_ids, rel_ids, TOP_K),
                    "retrieved": b_ids,
                    "latency_ms": b_latency,
                },
                "agent": {
                    "recall": recall_at_k(a_ids, rel_ids, TOP_K),
                    "retrieved": a_ids,
                    "intent": a_intent,
                    "tool_calls": a_tool_calls,
                    "latency_ms": a_latency,
                    "token_used": a_tokens,
                    "expected_intent": item.get("expected_intent", ""),
                },
            }

            if judge_faithfulness:
                if b_answer:
                    row["baseline"]["faithfulness"] = judge_faithfulness(question, b_answer, b_sources)["score"]
                if a_answer:
                    a_full = get_full_sources(a_ids, db)
                    row["agent"]["faithfulness"] = judge_faithfulness(question, a_answer, a_full)["score"]
                if b_answer:
                    row["baseline"]["relevancy"] = judge_answer_relevancy(question, b_answer)["score"]
                if a_answer:
                    row["agent"]["relevancy"] = judge_answer_relevancy(question, a_answer)["score"]

            results.append(row)
    finally:
        db.close()

    agg_b = aggregate([dict(r["baseline"], category=r["category"]) for r in results])
    agg_a = aggregate([dict(r["agent"], category=r["category"]) for r in results])

    report_path = os.path.join(settings.EVAL_REPORT_DIR, f"{datetime.now().strftime('%Y-%m-%d')}-comparison.md")
    write_report(report_path, args.agent_version, results, agg_b, agg_a)

    db = SessionLocal()
    try:
        write_eval_runs(db, results, args.agent_version)
    finally:
        db.close()

    print(f"\n完成: 共 {len(results)} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
