# -*- coding: utf-8 -*-
"""Phase 4:Agent 可靠性——工具硬超时、同工具失败熔断、LLM 指数退避。

为什么单独测这三件事:它们都是"失败路径"上的代码,正常跑评测永远走不到,
而恰恰是慢工具/端点抖动/连续失败时才决定链路是降级还是直接卡死。
"""
import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
import openai
import pytest
from langchain_core.messages import AIMessage

from app.services.agent import nodes
from app.services.llm import deepseek_provider as dp


def _state(**extra):
    base = {
        "messages": [],
        "question": "测试问题",
        "user_id": "u1",
        "session_id": "s1",
        "iteration": 0,
        "token_used": 0,
        "documents": [],
        "thoughts": [],
        "tool_calls_log": [],
        "searched_queries": [],
    }
    base.update(extra)
    return base


class _FakeTool:
    """替身工具:记录调用次数,可配置耗时/异常。"""

    def __init__(self, *, delay: float = 0.0, error: Exception = None):
        self.delay = delay
        self.error = error
        self.calls = 0

    def invoke(self, args):
        self.calls += 1
        if self.delay:
            import time

            time.sleep(self.delay)
        if self.error:
            raise self.error
        return json.dumps({"ok": True}, ensure_ascii=False)


# ---------- 工具硬超时 ----------
def test_slow_tool_times_out_and_reports_timeout_status():
    slow = _FakeTool(delay=0.5)
    status, result = nodes._call_tool(
        slow, "slow_tool", {}, _state(), timeout=0.05
    )
    assert status == "timeout"
    assert "超时" in json.loads(result)["error"]
    # 超时只表示"不再等待",线程仍在跑;这里确认它确实被调起过
    assert slow.calls == 1


def test_fast_tool_still_succeeds_under_timeout():
    fast = _FakeTool()
    status, result = nodes._call_tool(
        fast, "fast_tool", {}, _state(), timeout=5
    )
    assert status == "success"
    assert json.loads(result)["ok"] is True


def test_tool_exception_is_error_not_timeout():
    broken = _FakeTool(error=RuntimeError("db down"))
    status, result = nodes._call_tool(broken, "broken", {}, _state(), timeout=5)
    assert status == "error"
    assert "db down" in result


# ---------- 同工具失败熔断 ----------
def _tool_call_message(name="flaky", call_id="call_1"):
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": {}, "id": call_id, "type": "tool_call"}],
    )


def test_breaker_short_circuits_after_threshold_failures(monkeypatch):
    flaky = _FakeTool()
    monkeypatch.setitem(nodes.TOOL_MAP, "flaky", flaky)
    prior_failures = [
        {"tool": "flaky", "status": "error", "result": "boom", "tool_call_id": f"old{i}"}
        for i in range(nodes.MAX_TOOL_FAILURES)
    ]
    state = _state(
        messages=[_tool_call_message()],
        tool_calls_log=prior_failures,
    )

    update = nodes.execute_tool(state)

    assert flaky.calls == 0, "熔断后不应再真调工具"
    log = update["tool_calls_log"][-1]
    assert log["status"] == "error"
    assert "熔断" in json.loads(log["result"])["error"]


def test_breaker_not_tripped_below_threshold(monkeypatch):
    flaky = _FakeTool()
    monkeypatch.setitem(nodes.TOOL_MAP, "flaky", flaky)
    state = _state(
        messages=[_tool_call_message()],
        tool_calls_log=[{"tool": "flaky", "status": "timeout", "result": "t"}],
    )

    update = nodes.execute_tool(state)

    assert flaky.calls == 1, "未达阈值应正常调用"
    assert update["tool_calls_log"][-1]["status"] == "success"


# ---------- LLM 指数退避 ----------
class _FlakyRunnable:
    def __init__(self, failures, exc):
        self.failures = failures
        self.exc = exc
        self.calls = 0

    def invoke(self, inputs):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.exc
        return "ok"


def _timeout_error():
    return openai.APITimeoutError(request=httpx.Request("POST", "https://example.test"))


def test_transient_error_retried_with_exponential_backoff(monkeypatch):
    sleeps = []
    monkeypatch.setattr(dp.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(
        dp,
        "settings",
        SimpleNamespace(LLM_MAX_ATTEMPTS=3, LLM_RETRY_BASE_DELAY=1.0),
    )
    runnable = _FlakyRunnable(failures=2, exc=_timeout_error())

    assert dp.invoke_with_retry(runnable, "input", label="t") == "ok"
    assert runnable.calls == 3
    assert len(sleeps) == 2
    # 第 2 次退避明显长于第 1 次(指数增长),抖动上限 0.25s
    assert 0.99 <= sleeps[0] <= 1.26
    assert 1.99 <= sleeps[1] <= 2.26


def test_non_transient_error_not_retried(monkeypatch):
    sleeps = []
    monkeypatch.setattr(dp.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(
        dp,
        "settings",
        SimpleNamespace(LLM_MAX_ATTEMPTS=3, LLM_RETRY_BASE_DELAY=1.0),
    )
    runnable = _FlakyRunnable(failures=3, exc=ValueError("bad request"))

    with pytest.raises(ValueError):
        dp.invoke_with_retry(runnable, "input")
    assert runnable.calls == 1, "400 类确定性错误重试没意义"
    assert sleeps == []


def test_transient_classification():
    assert dp.is_transient_llm_error(_timeout_error())
    assert dp.is_transient_llm_error(
        openai.APIConnectionError(request=httpx.Request("POST", "https://example.test"))
    )
    assert not dp.is_transient_llm_error(ValueError("bad request"))
