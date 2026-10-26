# -*- coding: utf-8 -*-
"""评测质量门禁:读取 run_eval 产出的 JSON 摘要,按阈值判定本次结果是否放行。

用法:
    python eval/eval_gate.py                       # 取 eval/reports 下最新的 *-comparison*.json
    python eval/eval_gate.py 路径/to/summary.json  # 指定摘要
    python eval/eval_gate.py --min pass_rate=0.85  # 临时覆盖某条阈值
    python eval/eval_gate.py --list                # 查看当前阈值

退出码:0 = 全部达标,1 = 有指标未达标或数据缺失(可直接用于 CI 阻断)。

设计取舍:
- 只读 JSON,不连 DB/不调模型,保证门禁本身零外部依赖、可在 CI 里秒级跑完。
- 指标为 None 视为"无数据 => 不通过",避免裁判全挂时被静默放行。
- 阈值口径与 eval 报告一致,阈值本身是工程约定,改阈值需同步改本文件并在升级笔记留痕。
"""
import argparse
import glob
import json
import os
import sys
from typing import Any, Dict, Optional

REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")

# 默认阈值:略低于当前基线,留出模型抖动的余量,但足以拦住明显退化
DEFAULT_THRESHOLDS: Dict[str, float] = {
    "recall@k": 0.90,          # 文档级召回
    "context_recall": 0.80,    # 证据是否撑得起标准答案(RAGAS 口径)
    "faithfulness": 0.85,
    "answer_relevancy": 0.90,
    "answer_coverage": 0.80,
    "pass_rate": 0.90,
    "routing_accuracy": 0.90,
}


def latest_summary() -> Optional[str]:
    # 只认「基线」摘要(*-comparison.json),排除消融的带 tag 摘要(*-comparison-<tag>.json),
    # 否则同一天跑完消融后门禁会误拿消融结果当基线。
    paths = glob.glob(os.path.join(REPORT_DIR, "*-comparison.json"))
    if not paths:
        return None
    return max(paths, key=os.path.getmtime)


# 门禁键名 -> 摘要 metrics 里的字段名(报告展示用 recall@k / answer_relevancy,
# 摘要里沿用 run_eval 内部字段 recall / relevancy,这里做一层映射)
GATE_TO_METRIC = {
    "recall@k": "recall",
    "answer_relevancy": "relevancy",
}


def _get(summary: Dict[str, Any], key: str) -> Optional[float]:
    if key in ("pass_rate", "routing_accuracy"):
        return summary.get(key)
    metric_key = GATE_TO_METRIC.get(key, key)
    return (summary.get("metrics") or {}).get(metric_key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent 评测质量门禁")
    parser.add_argument("summary", nargs="?", help="JSON 摘要路径(默认取最新)")
    parser.add_argument(
        "--min", action="append", default=[], metavar="KEY=VALUE",
        help="覆盖阈值,可重复,如 --min pass_rate=0.85",
    )
    parser.add_argument("--list", action="store_true", help="打印当前阈值后退出")
    args = parser.parse_args()

    thresholds = dict(DEFAULT_THRESHOLDS)
    for item in args.min:
        if "=" not in item:
            print(f"[参数错误] --min 需要 KEY=VALUE 形式: {item}")
            return 2
        key, value = item.split("=", 1)
        key = key.strip()
        if key not in thresholds:
            print(f"[参数错误] 未知阈值键: {key}(可用: {', '.join(thresholds)})")
            return 2
        thresholds[key] = float(value)

    if args.list:
        for key, value in thresholds.items():
            print(f"{key}: {value}")
        return 0

    path = args.summary or latest_summary()
    if not path:
        print(f"[门禁失败] 在 {REPORT_DIR} 下找不到 *-comparison.json(基线摘要),请先跑 eval/run_eval.py")
        return 1
    if not os.path.exists(path):
        print(f"[门禁失败] 摘要不存在: {path}")
        return 1

    with open(path, encoding="utf-8") as f:
        summary = json.load(f)

    print(f"摘要: {path}")
    print(f"版本: {summary.get('agent_version')}  裁判: {summary.get('judge')}  "
          f"条数: {summary.get('count')}  生成: {summary.get('generated_at')}")
    print("")
    print("| 指标 | 实测 | 阈值 | 结果 |")
    print("|---|---|---|---|")

    failed = []
    for key, threshold in thresholds.items():
        value = _get(summary, key)
        if value is None:
            print(f"| {key} | 无数据 | {threshold:.2f} | 未通过 |")
            failed.append(f"{key}(无数据)")
            continue
        ok = value >= threshold
        print(f"| {key} | {value:.3f} | {threshold:.2f} | {'通过' if ok else '未通过'} |")
        if not ok:
            failed.append(f"{key}={value:.3f}<{threshold:.2f}")

    print("")
    if failed:
        print(f"[门禁未通过] {len(failed)} 项不达标: " + "、".join(failed))
        return 1
    print("[门禁通过] 全部指标达到阈值")
    return 0


if __name__ == "__main__":
    sys.exit(main())
