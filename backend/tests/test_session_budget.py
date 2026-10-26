# -*- coding: utf-8 -*-
"""Phase 4:每会话 token/金额双预算——超预算必须硬停并降级，而不是继续烧额度。"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api.routes import agent as agent_route
from app.models.agent_session import AgentSession


def _session(tokens=0, cost=0.0):
    return AgentSession(total_tokens=tokens, total_cost_cny=cost)


def test_budget_not_exhausted_within_limits(monkeypatch):
    monkeypatch.setattr(agent_route.settings, "AGENT_SESSION_TOKEN_BUDGET", 1000)
    monkeypatch.setattr(agent_route.settings, "AGENT_SESSION_COST_BUDGET_CNY", 1.0)
    assert agent_route._session_budget_exhausted(_session(999, 0.5)) is None


def test_token_budget_hard_stop(monkeypatch):
    monkeypatch.setattr(agent_route.settings, "AGENT_SESSION_TOKEN_BUDGET", 1000)
    monkeypatch.setattr(agent_route.settings, "AGENT_SESSION_COST_BUDGET_CNY", 1.0)
    reason = agent_route._session_budget_exhausted(_session(1000, 0.0))
    assert reason and "1000" in reason


def test_cost_budget_hard_stop(monkeypatch):
    monkeypatch.setattr(agent_route.settings, "AGENT_SESSION_TOKEN_BUDGET", 100000)
    monkeypatch.setattr(agent_route.settings, "AGENT_SESSION_COST_BUDGET_CNY", 1.0)
    reason = agent_route._session_budget_exhausted(_session(10, 1.2))
    assert reason and "1.20" in reason


def test_legacy_session_with_null_usage_is_not_blocked(monkeypatch):
    monkeypatch.setattr(agent_route.settings, "AGENT_SESSION_TOKEN_BUDGET", 1000)
    monkeypatch.setattr(agent_route.settings, "AGENT_SESSION_COST_BUDGET_CNY", 1.0)
    assert agent_route._session_budget_exhausted(_session(None, None)) is None


def test_turn_cost_uses_configured_unit_price(monkeypatch):
    monkeypatch.setattr(agent_route.settings, "AGENT_COST_PER_1K_TOKENS_CNY", 0.002)
    assert agent_route._turn_cost_cny(1000) == 0.002
    assert agent_route._turn_cost_cny(2500) == 0.005


def test_budget_exceeded_stream_degrades_without_llm(monkeypatch):
    monkeypatch.setattr(agent_route.settings, "AGENT_SESSION_TOKEN_BUDGET", 1000)
    monkeypatch.setattr(agent_route.settings, "AGENT_SESSION_COST_BUDGET_CNY", 1.0)
    chunks = list(agent_route._budget_exceeded_stream(_session(1000, 0.0), "达上限"))
    assert len(chunks) == 3
    assert "budget_exceeded" in chunks[0]
    payload = json.loads(chunks[1].removeprefix("data: ").strip())
    assert payload["type"] == "final_answer"
    assert "预算已用尽" in payload["answer"]
    assert chunks[2].strip().endswith("[DONE]")
