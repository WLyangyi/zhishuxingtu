# -*- coding: utf-8 -*-
"""「去记忆」消融:多轮追问下,上下文承接对第二轮答案的影响。

为什么要单独跑:单轮 eval 里记忆几乎不起作用(preference 注入仅影响提示词),
真正吃记忆的是「第二个项目的亮点是什么」这类指代型追问。
做法:
  with_memory   两轮共用一个 thread_id,checkpoint 把第一轮消息带进第二轮
  without_memory 每轮用独立 thread_id,等价于关掉会话记忆
指标(不花裁判额度,全确定性):
  turn2 recall@k       第二轮检索是否仍命中相关文档
  turn2 关键词命中率    第二轮答案是否出现预期实体(如「高并发」「Mini 3」)
  avg token / tool_calls 第二轮平均开销

用法:
    .venv\\Scripts\\python.exe eval/ablation_memory.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 离线批跑不需要云端 trace。注意不能靠清空 LANGFUSE_* key 来关:
# PowerShell 里把环境变量设成空串等价于删除变量,最终仍会回退读 .env 里的真 key。
os.environ["LANGFUSE_ENABLED"] = "false"
# 与其余消融组/冻结基线保持同一张图(A′ 多 Agent),否则记忆对比的基线不可比。
os.environ.setdefault("AGENT_MULTI_AGENT", "true")

# 与 run_eval.py 同一套本机 workaround(WMI 卡死 / transformers→torch 连带阻塞)
sys.modules.setdefault("transformers", None)
import platform as _platform  # noqa: E402

_platform.win32_ver = lambda *a, **k: ("", "", "", "")
_platform.machine = lambda: os.environ.get("PROCESSOR_ARCHITECTURE") or "AMD64"

from app.core.config import settings  # noqa: E402
from app.services import init_hybrid_search, init_vector_store  # noqa: E402

CASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "multi_turn_set.json")
TOP_K = 5


def run_turn(question: str, thread_id: str, user_id: str) -> dict:
    from app.services.agent.graph import build_input, get_graph
    from app.services.observability.langfuse_trace import build_stream_config
    from app.services.tools.context import ToolContext, set_tool_context

    set_tool_context(ToolContext(user_id=user_id, session_id="mem-ablation"))
    graph = get_graph()
    input_data = build_input(question, session_id="mem-ablation", user_id=user_id)

    answer, documents, seen = "", [], set()
    for step in graph.stream(input_data, config=build_stream_config(thread_id)):
        for _, value in step.items():
            if value.get("answer"):
                answer = value["answer"]
            for doc in value.get("documents") or []:
                doc_id = doc.get("id")
                if doc_id and doc_id not in seen:
                    seen.add(doc_id)
                    documents.append(doc)

    state = {"configurable": {"thread_id": thread_id}}
    values = graph.get_state(state).values or {}
    return {
        "answer": answer,
        "retrieved": [d["id"] for d in documents],
        "tool_calls": len(values.get("tool_calls_log") or []),
        "token_used": values.get("token_used") or 0,
    }


def recall_at_k(retrieved, relevant, k=TOP_K):
    if not relevant:
        return None
    return len(set(retrieved[:k]) & set(relevant)) / len(relevant)


def run_mode(cases, mode: str, user_id: str) -> dict:
    print(f"\n[memory] === {mode} ===")
    turn2_recalls, turn2_hits, turn2_tokens, turn2_calls, details = [], [], [], [], []
    for case in cases:
        stamp = int(time.time() * 1000)
        base_thread = f"mem-{mode}-{case['id']}-{stamp}"
        prev_token = 0
        last = {}
        for index, turn in enumerate(case["turns"]):
            thread_id = base_thread if mode == "with_memory" else f"{base_thread}-t{index}"
            result = run_turn(turn["question"], thread_id, user_id)
            if index == 1:
                recall = recall_at_k(result["retrieved"], turn.get("relevant_doc_ids") or [])
                keywords = turn.get("expect_keywords") or []
                answer = result["answer"] or ""
                hit = any(k in answer for k in keywords) if keywords else None
                turn2_recalls.append(recall)
                turn2_hits.append(hit)
                turn2_tokens.append(max(0, result["token_used"] - prev_token))
                turn2_calls.append(result["tool_calls"])
                last = {
                    "id": case["id"],
                    "question": turn["question"],
                    "answer": answer[:200],
                    "recall": recall,
                    "keyword_hit": hit,
                }
            else:
                # 同一线程的 token_used 是累计值,第二轮要减掉第一轮;换线程则从 0 重新计
                prev_token = result["token_used"] if mode == "with_memory" else 0
        print(f"  {case['id']} turn2: recall={last.get('recall')} keyword_hit={last.get('keyword_hit')}")
        details.append(last)

    def mean(values):
        picked = [v for v in values if v is not None]
        return round(sum(picked) / len(picked), 3) if picked else None

    return {
        "turns": len(details) * 2,
        "turn2_recall": mean(turn2_recalls),
        "turn2_keyword_hit": mean([1.0 if h else 0.0 for h in turn2_hits if h is not None]),
        "avg_token": round(sum(turn2_tokens) / len(turn2_tokens), 1) if turn2_tokens else 0,
        "avg_tool_calls": mean(turn2_calls),
        "cases": details,
    }


def write_report(summary: dict) -> str:
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = settings.EVAL_REPORT_DIR
    os.makedirs(report_dir, exist_ok=True)

    json_path = os.path.join(report_dir, f"{today}-ablation-memory.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with_mem = summary["with_memory"]
    without_mem = summary["without_memory"]
    lines = [
        f"# 去记忆消融({today})",
        "",
        "> 口径:两轮共享 thread_id(有记忆) vs 每轮独立 thread_id(无记忆);3 条指代型追问。",
        "",
        "| 模式 | turn2 recall@k | turn2 关键词命中率 | 平均 token | 平均工具调用 |",
        "|---|---|---|---|---|",
        f"| with_memory | {with_mem['turn2_recall']} | {with_mem['turn2_keyword_hit']} | "
        f"{with_mem['avg_token']} | {with_mem['avg_tool_calls']} |",
        f"| without_memory | {without_mem['turn2_recall']} | {without_mem['turn2_keyword_hit']} | "
        f"{without_mem['avg_token']} | {without_mem['avg_tool_calls']} |",
        "",
        "## 逐条明细",
        "",
        "| case | 第二轮问题 | 有记忆 recall / 命中 | 无记忆 recall / 命中 |",
        "|---|---|---|---|",
    ]
    by_id_with = {c["id"]: c for c in with_mem["cases"]}
    for item in without_mem["cases"]:
        w = by_id_with.get(item["id"], {})
        lines.append(
            f"| {item['id']} | {item['question']} | {w.get('recall')} / {w.get('keyword_hit')} | "
            f"{item.get('recall')} / {item.get('keyword_hit')} |"
        )
    lines.append("")

    md_path = os.path.join(report_dir, f"{today}-ablation-memory.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return md_path


def main() -> int:
    init_vector_store(settings.FAISS_INDEX_PATH)
    init_hybrid_search()

    with open(CASE_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    from app.db.session import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("[失败] 无用户")
            return 1
        user_id = user.id
    finally:
        db.close()

    summary = {
        "with_memory": run_mode(cases, "with_memory", user_id),
        "without_memory": run_mode(cases, "without_memory", user_id),
    }
    path = write_report(summary)
    print(f"\n[memory] 报告已写入: {path}")
    print(f"有记忆: {summary['with_memory']}")
    print(f"无记忆: {summary['without_memory']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
