# -*- coding: utf-8 -*-
"""阶段1b:路由回归硬门禁纯函数测试(多数票 + 门禁判定)。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.eval_route_gate import (  # noqa: E402
    BOUNDARY_THRESHOLD,
    EVAL_ROUTING_THRESHOLD,
    evaluate_gate,
    majority_vote,
)


def test_majority_vote_picks_most_common():
    assert majority_vote(["knowledge", "knowledge", "web_search"]) == "knowledge"


def test_majority_vote_tie_picks_first():
    assert majority_vote(["knowledge", "web_search"]) == "knowledge"


def test_majority_vote_empty():
    assert majority_vote([]) == ""


def test_gate_passes_when_both_meet_threshold():
    passed, failed = evaluate_gate(BOUNDARY_THRESHOLD, EVAL_ROUTING_THRESHOLD)
    assert passed
    assert failed == []


def test_gate_fails_when_boundary_below_threshold():
    passed, failed = evaluate_gate(0.5, EVAL_ROUTING_THRESHOLD)
    assert not passed
    assert any("boundary_accuracy" in f for f in failed)


def test_gate_fails_when_eval_routing_missing():
    passed, failed = evaluate_gate(BOUNDARY_THRESHOLD, None)
    assert not passed
    assert any("无数据" in f for f in failed)


def test_gate_fails_when_eval_routing_below_threshold():
    passed, failed = evaluate_gate(BOUNDARY_THRESHOLD, 0.5)
    assert not passed
    assert any("eval_routing_accuracy" in f for f in failed)
