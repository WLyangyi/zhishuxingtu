# -*- coding: utf-8 -*-
"""回归门禁的自动化证据:验证 eval_gate 能放行达标结果、拦住人为回退。

对应 Phase 3 验收标准「门禁能拦住一次人为回退」。
"""
import importlib.util
import json
import os
import sys

import pytest

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_gate():
    path = os.path.join(BACKEND_ROOT, "eval", "eval_gate.py")
    spec = importlib.util.spec_from_file_location("eval_gate_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PASSING = {
    "agent_version": "agent-v1",
    "judge": "glm / glm-5.3-flash",
    "generated_at": "2026-10-27T01:00:00",
    "count": 50,
    "metrics": {
        "recall": 0.983,
        "faithfulness": 0.911,
        "relevancy": 0.954,
        "context_recall": 0.920,
        "answer_coverage": 0.900,
    },
    "pass_rate": 0.96,
    "routing_accuracy": 0.98,
}


def _run(monkeypatch, tmp_path, summary, name="2026-10-27-comparison.json"):
    gate = _load_gate()
    monkeypatch.setattr(gate, "REPORT_DIR", str(tmp_path))
    target = tmp_path / name
    target.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eval_gate.py"])
    return gate.main()


def test_gate_passes_on_baseline(tmp_path, monkeypatch, capsys):
    assert _run(monkeypatch, tmp_path, PASSING) == 0
    assert "门禁通过" in capsys.readouterr().out


def test_gate_blocks_recall_regression(tmp_path, monkeypatch, capsys):
    broken = dict(PASSING, metrics=dict(PASSING["metrics"], recall=0.50))
    assert _run(monkeypatch, tmp_path, broken) == 1
    assert "门禁未通过" in capsys.readouterr().out


def test_gate_treats_missing_metric_as_failure(tmp_path, monkeypatch):
    broken = dict(PASSING, metrics=dict(PASSING["metrics"], faithfulness=None))
    assert _run(monkeypatch, tmp_path, broken) == 1


def test_gate_ignores_tagged_ablation_summary(tmp_path, monkeypatch):
    # 只有消融摘要时,门禁不应把它当基线放行
    assert _run(
        monkeypatch, tmp_path, PASSING, name="2026-10-27-comparison-ablation-no_bm25.json"
    ) == 1


def test_gate_rejects_unknown_threshold_key(tmp_path, monkeypatch, capsys):
    gate = _load_gate()
    monkeypatch.setattr(gate, "REPORT_DIR", str(tmp_path))
    (tmp_path / "2026-10-27-comparison.json").write_text(json.dumps(PASSING), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eval_gate.py", "--min", "nope=0.1"])
    assert gate.main() == 2


def test_gate_blocks_decline_that_absolute_threshold_still_allows(
    tmp_path, monkeypatch, capsys
):
    """0.983 → 0.950 仍高于绝对阈值 0.90,只有基线比对能拦住这次退化。"""
    gate = _load_gate()
    monkeypatch.setattr(gate, "REPORT_DIR", str(tmp_path))
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(PASSING), encoding="utf-8")
    current = dict(PASSING, metrics=dict(PASSING["metrics"], recall=0.95))
    (tmp_path / "2026-10-27-comparison.json").write_text(
        json.dumps(current), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["eval_gate.py", "--baseline", str(baseline_path)])
    assert gate.main() == 1
    assert "回退" in capsys.readouterr().out


def test_gate_allows_regression_within_limit(tmp_path, monkeypatch):
    gate = _load_gate()
    monkeypatch.setattr(gate, "REPORT_DIR", str(tmp_path))
    baseline = dict(PASSING, metrics=dict(PASSING["metrics"], recall=0.99))
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    (tmp_path / "2026-10-27-comparison.json").write_text(
        json.dumps(PASSING), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["eval_gate.py", "--baseline", str(baseline_path)])
    # 0.99 → 0.983 只回退 0.007,未超 0.02
    assert gate.main() == 0


def test_gate_fails_when_baseline_missing(tmp_path, monkeypatch, capsys):
    gate = _load_gate()
    monkeypatch.setattr(gate, "REPORT_DIR", str(tmp_path))
    (tmp_path / "2026-10-27-comparison.json").write_text(
        json.dumps(PASSING), encoding="utf-8"
    )
    monkeypatch.setattr(
        sys, "argv", ["eval_gate.py", "--baseline", str(tmp_path / "nope.json")]
    )
    assert gate.main() == 1
    assert "基线摘要不存在" in capsys.readouterr().out
