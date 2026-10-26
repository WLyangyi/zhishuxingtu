# -*- coding: utf-8 -*-
"""Phase 3 消融实验执行器(方案 §5.5 的 7 组配置)。

配置与验证目标:
  full              基线(对照组,同口径但跳过裁判,用于延迟/token 对比)
  no_reranker       去精排 —— 精排对 single_doc/simple_fact 召回的贡献
  no_bm25           去 BM25 纯向量 —— 关键词对专有名词召回的贡献
  no_three_check    去三查 —— 文档评级/幻觉核对/答案质量对生成质量的贡献(需裁判)
  force_knowledge   去意图路由 —— 路由对简单题 token/延迟的贡献
  no_memory         去记忆 —— 多轮追问的上下文承接能力(独立多轮 case)
  overlap0          分块重叠 0 —— 重叠对召回的影响(需先按重叠 0 重建独立索引)

跑法(按方案 §5.5 的两步走):
  第一步:全部 --skip-judge,只算 recall / 路由 / 延迟 / token(省裁判额度)。
          python eval/ablation_runner.py
  第二步:对最可疑的配置追加带裁判的跑法。
          python eval/ablation_runner.py --configs no_three_check --judge

说明:
  - 每组跑 run_eval.py 的子进程,报告按 --tag 落成 <日期>-comparison-ablation-<name>.{md,json},
    互不覆盖,也不影响冻结的基线摘要(*-comparison.json)。
  - 消融只关心 agent 侧,统一带 --agent-only 跳过旧基线,省掉一半时间。
  - overlap0 会先按 OVERLAP_RATIO=0 重建一份独立向量索引(不动生产索引)。
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(BACKEND_ROOT, "eval", "reports")
PYTHON = sys.executable

# 每组配置 = {环境变量覆盖};值为空表示对照组
CONFIGS = {
    "full": {},
    "no_reranker": {"USE_RERANKER": "false"},
    "no_bm25": {"USE_HYBRID_SEARCH": "false"},
    "no_three_check": {"USE_THREE_CHECK": "false"},
    "force_knowledge": {"FORCE_INTENT": "knowledge"},
    "overlap0": {},  # 额外先重建索引,见 run_overlap_reindex
}

OVERLAP0_INDEX = os.path.join(BACKEND_ROOT, "data", "ablation-overlap0-faiss")


def run_overlap_reindex() -> bool:
    """按 OVERLAP_RATIO=0 重建独立索引;失败则不跑 overlap0 组,避免拿生产索引冒充消融结果。"""
    print("[ablation] 重建 overlap0 索引 ...")
    cmd = [PYTHON, "-u", os.path.join("eval", "ablation_reindex.py"),
           "--out", OVERLAP0_INDEX, "--overlap", "0"]
    proc = subprocess.run(cmd, cwd=BACKEND_ROOT, env=os.environ.copy())
    return proc.returncode == 0


def run_config(name: str, judge: bool, limit: int) -> bool:
    overrides = dict(CONFIGS[name])
    if name == "overlap0":
        overrides["FAISS_INDEX_PATH"] = OVERLAP0_INDEX
        overrides["OVERLAP_RATIO"] = "0"

    env = os.environ.copy()
    env.update(overrides)
    env.setdefault("AGENT_MULTI_AGENT", "true")  # 与冻结基线同图

    tag = f"ablation-{name}"
    cmd = [
        PYTHON, "-u", os.path.join("eval", "run_eval.py"),
        "--agent-only", "--agent-version", tag, "--tag", tag,
    ]
    if not judge:
        cmd.append("--skip-judge")
    if limit:
        cmd.extend(["--limit", str(limit)])

    log_path = os.path.join(REPORT_DIR, f"{datetime.now().strftime('%Y-%m-%d')}-{tag}.log")
    os.makedirs(REPORT_DIR, exist_ok=True)
    print(f"\n[ablation] === {name} === 覆盖: {overrides or '(无,对照组)'}")
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.run(cmd, cwd=BACKEND_ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    print(f"[ablation] {name} 结束 exit={proc.returncode},日志: {log_path}")
    return proc.returncode == 0


def run_memory() -> bool:
    print("\n[ablation] === no_memory === 多轮上下文承接")
    cmd = [PYTHON, "-u", os.path.join("eval", "ablation_memory.py")]
    proc = subprocess.run(cmd, cwd=BACKEND_ROOT, env=os.environ.copy())
    return proc.returncode == 0


def load_summary(name: str) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(REPORT_DIR, f"{today}-comparison-ablation-{name}.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_memory_summary() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(REPORT_DIR, f"{today}-ablation-memory.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fmt(value, digits=3):
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def write_report(names) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    summaries = {name: load_summary(name) for name in names}
    base = summaries.get("full") or {}
    base_recall = (base.get("metrics") or {}).get("recall")

    lines = [
        f"# 消融实验报告({today})",
        "",
        "> 每组的执行日志见同目录 `*-ablation-<name>.log`;逐条明细见 `*-comparison-ablation-<name>.md`。",
        "> 口径:agent 侧单跑(--agent-only),除标注「裁判」的组外均 --skip-judge,只比 recall/路由/延迟/token。",
        "",
        "## 配置对比",
        "",
        "| 配置 | 条数 | recall@k | 路由准确率 | 平均工具调用 | 平均 token | 平均延迟 ms | 与 full 的 recall 差 |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for name in names:
        s = summaries.get(name) or {}
        metrics = s.get("metrics") or {}
        recall = metrics.get("recall")
        delta = "—"
        if recall is not None and base_recall is not None:
            delta = f"{recall - base_recall:+.3f}"
        lines.append(
            f"| {name} | {fmt(s.get('count'))} | {fmt(recall)} | {fmt(s.get('routing_accuracy'))} | "
            f"{fmt(s.get('avg_tool_calls'), 2)} | {fmt(s.get('avg_token_used'), 0)} | "
            f"{fmt(s.get('avg_latency_ms'), 0)} | {delta} |"
        )

    judged = [n for n in names if (summaries.get(n) or {}).get("judge") not in (None, "skip-judge")]
    if judged:
        lines += [
            "",
            "## 带裁判的组(生成质量)",
            "",
            "| 配置 | faithfulness | answer_relevancy | context_recall | answer_coverage | pass 率 |",
            "|---|---|---|---|---|---|",
        ]
        for name in judged:
            s = summaries[name]
            m = s.get("metrics") or {}
            pr = s.get("pass_rate")
            lines.append(
                f"| {name} | {fmt(m.get('faithfulness'))} | {fmt(m.get('relevancy'))} | "
                f"{fmt(m.get('context_recall'))} | {fmt(m.get('answer_coverage'))} | "
                f"{fmt(pr * 100 if pr is not None else None, 1)}% |"
            )

    memory = load_memory_summary()
    if memory:
        lines += [
            "",
            "## 去记忆(多轮追问,独立 case set)",
            "",
            "| 模式 | 轮次 | turn2 recall@k | turn2 关键词命中率 | 平均 token | 平均工具调用 |",
            "|---|---|---|---|---|---|",
        ]
        for mode in ("with_memory", "without_memory"):
            m = memory.get(mode) or {}
            lines.append(
                f"| {mode} | {fmt(m.get('turns'))} | {fmt(m.get('turn2_recall'))} | "
                f"{fmt(m.get('turn2_keyword_hit'))} | {fmt(m.get('avg_token'), 0)} | "
                f"{fmt(m.get('avg_tool_calls'), 2)} |"
            )

    lines += [
        "",
        "## 读表提醒",
        "",
        "- 差值绝对值小于 0.02 视为抖动,不声称有效(方案 §5.5)。",
        "- 延迟包含网络与模型排队,只作趋势参考。",
        "- 关闭三查会省两次 LLM 调用,token 下降属预期;faithfulness 是否下降要看带裁判那一组。",
        "",
    ]

    path = os.path.join(REPORT_DIR, f"{today}-ablation.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3 消融实验执行器")
    parser.add_argument(
        "--configs", default="full,no_reranker,no_bm25,no_three_check,force_knowledge,overlap0",
        help="要跑的配置(逗号分隔);含 no_memory 时跑多轮记忆消融",
    )
    parser.add_argument("--judge", action="store_true", help="带裁判跑(慢,只在需要生成质量指标时用)")
    parser.add_argument("--limit", type=int, default=0, help="每组只跑前 N 条(冒烟验证)")
    args = parser.parse_args()

    names = [n.strip() for n in args.configs.split(",") if n.strip()]
    unknown = [n for n in names if n not in CONFIGS and n != "no_memory"]
    if unknown:
        print(f"[参数错误] 未知配置: {unknown};可用: {list(CONFIGS) + ['no_memory']}")
        return 2

    ran = []
    if "overlap0" in names and not run_overlap_reindex():
        print("[ablation] overlap0 索引重建失败,跳过该组(不拿生产索引冒充)")
        names = [n for n in names if n != "overlap0"]

    for name in names:
        if name == "no_memory":
            if run_memory():
                ran.append("no_memory")
            continue
        if run_config(name, args.judge, args.limit):
            ran.append(name)

    report = write_report([n for n in names if n != "no_memory"])
    print(f"\n[ablation] 报告已写入: {report}")
    print(f"[ablation] 完成组: {ran}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
