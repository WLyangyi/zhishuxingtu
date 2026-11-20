# -*- coding: utf-8 -*-
"""core_intent 意图锚点 · 阶段 1a 主链路(TDD)。

任务 1.1:数据模型——AgentSession 加 core_intent/intent_version/intent_versions,
AgentState 加常驻字段 core_intent/intent_version 与临时字段 last_intent_change/
low_confidence_hint/pending_preference(turn_start_checkpoint_id 阶段 0 已有)。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.agent_session import AgentSession


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()
    engine.dispose()


# ---------- 任务 1.1:AgentSession 字段可读写 ----------

def test_agent_session_core_intent_fields_roundtrip(db):
    """AgentSession 三新字段可落库并读回,JSON 结构保持。"""
    import json

    core_intent = {
        "goal": "整理周报",
        "constraints": {"tone": "正式", "language": "中文"},
        "acceptance_criteria": ["覆盖本周三项产出"],
    }
    versions = [
        {
            "version": 1,
            "goal": "整理周报",
            "constraints": {"tone": "正式"},
            "acceptance_criteria": ["覆盖本周三项产出"],
            "change_type": "init",
            "source": "llm",
            "confidence": 0.9,
            "unmapped_keys": [],
            "ts": "2026-11-20T10:00:00",
        }
    ]
    session = AgentSession(
        id="s1",
        user_id="u1",
        title="测试",
        core_intent=json.dumps(core_intent, ensure_ascii=False),
        intent_version=1,
        intent_versions=json.dumps(versions, ensure_ascii=False),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    assert json.loads(session.core_intent)["goal"] == "整理周报"
    assert json.loads(session.core_intent)["constraints"]["tone"] == "正式"
    assert session.intent_version == 1
    assert json.loads(session.intent_versions)[0]["change_type"] == "init"
    assert json.loads(session.intent_versions)[0]["version"] == 1


def test_agent_session_core_intent_defaults_empty(db):
    """新建会话三字段默认为空/0,不破坏老数据。"""
    session = AgentSession(id="s2", user_id="u1", title="新会话")
    db.add(session)
    db.commit()
    db.refresh(session)

    assert session.core_intent in (None, "")
    assert session.intent_version in (None, 0)
    assert session.intent_versions in (None, "")


# ---------- 任务 1.1:AgentState 字段在 state 流转 ----------

def test_agent_state_has_core_intent_fields():
    """AgentState TypedDict 声明常驻 + 临时字段(结构检查)。"""
    from app.services.agent.state import AgentState

    annotations = AgentState.__annotations__
    for field in (
        "core_intent",
        "intent_version",
        "last_intent_change",
        "turn_start_checkpoint_id",
        "low_confidence_hint",
        "pending_preference",
    ):
        assert field in annotations, f"AgentState 缺少字段 {field}"


def test_agent_state_fields_flow_through_graph():
    """新字段经编译图流转:节点写入后,checkpoint 快照能读回,不丢字段。"""
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph

    from app.services.agent.state import AgentState

    def _writer(state: AgentState):
        return {
            "core_intent": {"goal": "g", "constraints": {}, "acceptance_criteria": []},
            "intent_version": 3,
            "last_intent_change": {"change_type": "append", "source": "llm", "ts": "t"},
            "low_confidence_hint": "拟将语气改为正式",
            "pending_preference": {"key": "language", "value": "英文", "scope": "global"},
        }

    g = StateGraph(AgentState)
    g.add_node("writer", _writer)
    g.add_edge(START, "writer")
    g.add_edge("writer", END)
    graph = g.compile(checkpointer=MemorySaver())

    config = {"configurable": {"thread_id": "flow-test"}}
    list(graph.stream({"messages": [], "question": "q"}, config=config))
    snap = graph.get_state(config)
    values = snap.values

    assert values["core_intent"]["goal"] == "g"
    assert values["intent_version"] == 3
    assert values["last_intent_change"]["change_type"] == "append"
    assert values["low_confidence_hint"] == "拟将语气改为正式"
    assert values["pending_preference"]["scope"] == "global"


# ---------- 任务 1.2:CoreIntentProposal schema + prompts ----------

def test_core_intent_proposal_full_fields():
    """CoreIntentProposal 路由字段 + 锚点字段同一次输出,字面量受约束。"""
    from app.services.agent.prompts import CoreIntentProposal

    proposal = CoreIntentProposal(
        intent="knowledge",
        reason="检索知识库",
        task_brief="查询前置条件",
        goal="整理周报",
        constraints=[
            {"key": "tone", "value": "正式", "op": "set"},
            {"key": "length", "value": "", "op": "delete"},
        ],
        acceptance_criteria=["覆盖三项产出"],
        change_type="append",
        reset_constraints=False,
        preference={"key": "language", "value": "英文", "scope": "global"},
        confidence=0.9,
    )
    assert proposal.intent == "knowledge"
    assert proposal.change_type == "append"
    assert proposal.constraints[0].op == "set"
    assert proposal.constraints[1].op == "delete"
    assert proposal.preference.scope == "global"
    assert proposal.confidence == 0.9


def test_core_intent_proposal_rejects_bad_literals():
    """change_type / op / scope / intent 非法值被 Pydantic 拒绝。"""
    from pydantic import ValidationError

    from app.services.agent.prompts import CoreIntentProposal

    with pytest.raises(ValidationError):
        CoreIntentProposal(intent="knowledge", change_type="bogus")
    with pytest.raises(ValidationError):
        CoreIntentProposal(intent="knowledge", constraints=[{"key": "k", "value": "v", "op": "x"}])
    with pytest.raises(ValidationError):
        CoreIntentProposal(intent="knowledge", preference={"key": "k", "value": "v", "scope": "x"})
    with pytest.raises(ValidationError):
        CoreIntentProposal(intent="bogus")


def test_core_intent_proposal_defaults():
    """锚点字段可缺省:无变更时 change_type=none、约束空、preference 空。"""
    from app.services.agent.prompts import CoreIntentProposal

    proposal = CoreIntentProposal(intent="knowledge", reason="r")
    assert proposal.change_type == "none"
    assert proposal.constraints == []
    assert proposal.preference is None
    assert proposal.reset_constraints is False


def test_intent_classify_prompt_has_anchor_rules():
    """INTENT_CLASSIFY_PROMPT 含 canonical key 与约束/偏好落点规则。"""
    from app.services.agent.prompts import INTENT_CLASSIFY_PROMPT

    assert "tone" in INTENT_CLASSIFY_PROMPT  # canonical key 归一
    assert "style" in INTENT_CLASSIFY_PROMPT  # style 独立
    assert "constraints" in INTENT_CLASSIFY_PROMPT  # 任务约束落点
    assert "global" in INTENT_CLASSIFY_PROMPT  # 偏好 scope 落点
    assert "change_type" in INTENT_CLASSIFY_PROMPT  # 四类变更
    assert "confidence" in INTENT_CLASSIFY_PROMPT  # 置信度
    assert "acceptance" in INTENT_CLASSIFY_PROMPT.lower()  # 验收标准
    assert "reset_constraints" in INTENT_CLASSIFY_PROMPT  # 清空约束


# ---------- 任务 1.3:四类变更 + 状态迁移表 ----------

def _proposal(**kw):
    from types import SimpleNamespace

    base = dict(
        intent="knowledge",
        reason="r",
        task_brief="",
        goal="",
        constraints=[],
        acceptance_criteria=[],
        change_type="none",
        reset_constraints=False,
        preference=None,
        confidence=0.9,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _op(key, value, op="set"):
    from types import SimpleNamespace

    return SimpleNamespace(key=key, value=value, op=op)


def _provider(proposal):
    class FakeStructured:
        def invoke(self, msgs):
            return proposal

    class FakeProvider:
        def with_structured_output(self, model):
            return FakeStructured()

    return FakeProvider()


def _classify(monkeypatch, proposal, state=None):
    from app.services.agent.nodes import intent_classify

    monkeypatch.setitem(
        intent_classify.__globals__, "get_deepseek_provider", lambda: _provider(proposal)
    )
    base = {"question": "测试", "thoughts": [], "user_id": "u1", "session_id": "s1"}
    base.update(state or {})
    return intent_classify(base)


def test_init_creates_anchor_version_1(monkeypatch):
    """无锚点 + init:建锚,version=1,写 last_intent_change。"""
    proposal = _proposal(
        change_type="init",
        goal="整理周报",
        constraints=[_op("tone", "正式")],
        acceptance_criteria=["覆盖三项产出"],
    )
    out = _classify(monkeypatch, proposal)
    assert out["core_intent"]["goal"] == "整理周报"
    assert out["core_intent"]["constraints"] == {"tone": "正式"}
    assert out["core_intent"]["acceptance_criteria"] == ["覆盖三项产出"]
    assert out["intent_version"] == 1
    assert out["last_intent_change"]["change_type"] == "init"
    assert out["last_intent_change"]["source"] == "llm"


def test_append_merges_constraints_bumps_version(monkeypatch):
    """有锚点 + append:合并约束,goal 不变,version+1。"""
    current = {
        "goal": "整理周报",
        "constraints": {"tone": "正式"},
        "acceptance_criteria": ["覆盖三项产出"],
    }
    proposal = _proposal(change_type="append", constraints=[_op("length", "简短")])
    out = _classify(monkeypatch, proposal, state={"core_intent": current, "intent_version": 1})
    assert out["core_intent"]["goal"] == "整理周报"  # goal 不变
    assert out["core_intent"]["constraints"] == {"tone": "正式", "length": "简短"}  # 合并
    assert out["core_intent"]["acceptance_criteria"] == ["覆盖三项产出"]  # acceptance 不变
    assert out["intent_version"] == 2
    assert out["last_intent_change"]["change_type"] == "append"


def test_append_delete_constraint(monkeypatch):
    """append + op=delete:移除指定约束,其余保留。"""
    current = {"goal": "g", "constraints": {"tone": "正式", "length": "简短"}, "acceptance_criteria": []}
    proposal = _proposal(change_type="append", constraints=[_op("length", "", op="delete")])
    out = _classify(monkeypatch, proposal, state={"core_intent": current, "intent_version": 1})
    assert out["core_intent"]["constraints"] == {"tone": "正式"}  # length 被删
    assert "length" not in out["core_intent"]["constraints"]


def test_revise_updates_goal_and_acceptance(monkeypatch):
    """有锚点 + revise:更新 goal/acceptance + 显式槽位覆盖,未提及约束保留,version+1。"""
    current = {
        "goal": "整理周报",
        "constraints": {"tone": "正式"},
        "acceptance_criteria": ["覆盖三项产出"],
    }
    proposal = _proposal(
        change_type="revise",
        goal="整理季度总结",
        acceptance_criteria=["覆盖全季度"],
        constraints=[_op("length", "详细")],
    )
    out = _classify(monkeypatch, proposal, state={"core_intent": current, "intent_version": 1})
    assert out["core_intent"]["goal"] == "整理季度总结"  # goal 更新
    assert out["core_intent"]["acceptance_criteria"] == ["覆盖全季度"]  # acceptance 更新
    assert out["core_intent"]["constraints"] == {"tone": "正式", "length": "详细"}  # 未提及保留+显式覆盖
    assert out["intent_version"] == 2
    assert out["last_intent_change"]["change_type"] == "revise"


def test_revise_reset_constraints_clears_old(monkeypatch):
    """revise + reset_constraints:先清空旧约束再应用。"""
    current = {"goal": "g", "constraints": {"tone": "正式", "length": "简短"}, "acceptance_criteria": []}
    proposal = _proposal(
        change_type="revise",
        reset_constraints=True,
        goal="新目标",
        constraints=[_op("tone", "轻松")],
    )
    out = _classify(monkeypatch, proposal, state={"core_intent": current, "intent_version": 1})
    assert out["core_intent"]["constraints"] == {"tone": "轻松"}  # 旧约束清空,只留新的
    assert out["core_intent"]["goal"] == "新目标"


def test_none_does_not_change_anchor(monkeypatch):
    """有锚点 + none:不改变锚点,不写 last_intent_change,不 bump 版本。"""
    current = {"goal": "g", "constraints": {"tone": "正式"}, "acceptance_criteria": []}
    proposal = _proposal(change_type="none")
    out = _classify(monkeypatch, proposal, state={"core_intent": current, "intent_version": 1})
    assert "core_intent" not in out  # 不触碰锚点
    assert "last_intent_change" not in out
    assert "intent_version" not in out


def test_no_anchor_append_downgrades_to_init(monkeypatch):
    """迁移表:无锚点 + append → 降级 init,version=1。"""
    proposal = _proposal(change_type="append", goal="建锚", constraints=[_op("tone", "正式")])
    out = _classify(monkeypatch, proposal)
    assert out["intent_version"] == 1
    assert out["last_intent_change"]["change_type"] == "init"  # 降级为 init
    assert out["core_intent"]["goal"] == "建锚"


def test_no_anchor_revise_downgrades_to_init(monkeypatch):
    """迁移表:无锚点 + revise → 降级 init,version=1。"""
    proposal = _proposal(change_type="revise", goal="建锚")
    out = _classify(monkeypatch, proposal)
    assert out["intent_version"] == 1
    assert out["last_intent_change"]["change_type"] == "init"


def test_has_anchor_init_ignored(monkeypatch):
    """迁移表:有锚点 + init → 忽略,不改变锚点。"""
    current = {"goal": "g", "constraints": {"tone": "正式"}, "acceptance_criteria": []}
    proposal = _proposal(change_type="init", goal="不该覆盖")
    out = _classify(monkeypatch, proposal, state={"core_intent": current, "intent_version": 1})
    assert "core_intent" not in out  # 忽略 init
    assert "last_intent_change" not in out


def test_force_intent_writes_history(monkeypatch):
    """FORCE_INTENT 消融:有锚点→append、无锚点→init,都写历史,source=force-intent。"""
    from app.services.agent import nodes

    # 无锚点 → init
    monkeypatch.setattr(nodes.settings, "FORCE_INTENT", "knowledge")
    monkeypatch.setattr(nodes, "get_deepseek_provider", lambda: _provider(_proposal()))
    out_init = nodes.intent_classify({"question": "q", "thoughts": [], "session_id": "s1"})
    assert out_init["intent_version"] == 1
    assert out_init["last_intent_change"]["change_type"] == "init"
    assert out_init["last_intent_change"]["source"] == "force-intent"

    # 有锚点 → append
    current = {"goal": "g", "constraints": {}, "acceptance_criteria": []}
    out_append = nodes.intent_classify(
        {"question": "q", "thoughts": [], "session_id": "s1", "core_intent": current, "intent_version": 1}
    )
    assert out_append["intent_version"] == 2
    assert out_append["last_intent_change"]["change_type"] == "append"
    assert out_append["last_intent_change"]["source"] == "force-intent"


# ---------- 任务 1.4:多信号触发权 + 约束规范化 + 词表 + 偏好去重 ----------

def test_low_confidence_blocks_append(monkeypatch):
    """低置信门槛挡所有变更:append 置信不足 → 不应用,写 low_confidence_hint。"""
    proposal = _proposal(change_type="append", constraints=[_op("tone", "轻松")], confidence=0.3)
    current = {"goal": "g", "constraints": {"tone": "正式"}, "acceptance_criteria": []}
    out = _classify(monkeypatch, proposal, state={"core_intent": current, "intent_version": 1})
    assert "core_intent" not in out  # 变更被挡,锚点不动
    assert "last_intent_change" not in out
    assert out["low_confidence_hint"]  # 含拟变更提示
    assert "轻松" in out["low_confidence_hint"]  # 提示含拟变更内容
    assert "重新" in out["low_confidence_hint"]  # 提示用户重述确认


def test_low_confidence_blocks_revise(monkeypatch):
    """低置信也挡 revise。"""
    proposal = _proposal(change_type="revise", goal="新目标", confidence=0.2)
    current = {"goal": "旧目标", "constraints": {}, "acceptance_criteria": []}
    out = _classify(monkeypatch, proposal, state={"core_intent": current, "intent_version": 1})
    assert "core_intent" not in out
    assert out["low_confidence_hint"]
    assert "新目标" in out["low_confidence_hint"]


def test_high_confidence_applies(monkeypatch):
    """高置信正常应用,不写提示。"""
    proposal = _proposal(change_type="append", constraints=[_op("tone", "轻松")], confidence=0.9)
    current = {"goal": "g", "constraints": {"tone": "正式"}, "acceptance_criteria": []}
    out = _classify(monkeypatch, proposal, state={"core_intent": current, "intent_version": 1})
    assert out["core_intent"]["constraints"] == {"tone": "轻松"}
    assert out["intent_version"] == 2
    assert "low_confidence_hint" not in out


def test_keyword_bonus_raises_confidence(monkeypatch):
    """多信号:关键词加分——基线置信略低但命中变更关键词,仍可触发。"""
    # 基线 0.5 低于门槛 0.6,但问题含"改为"加分后越过门槛
    proposal = _proposal(change_type="append", constraints=[_op("tone", "轻松")], confidence=0.5)
    current = {"goal": "g", "constraints": {"tone": "正式"}, "acceptance_criteria": []}
    out = _classify(
        monkeypatch, proposal,
        state={"core_intent": current, "intent_version": 1, "question": "请把语气改为轻松"},
    )
    assert out["core_intent"]["constraints"] == {"tone": "轻松"}  # 加分后应用
    assert "low_confidence_hint" not in out


def test_constraints_normalize_tone_key(monkeypatch):
    """约束键归一:语气/口吻 → tone。"""
    proposal = _proposal(change_type="init", goal="g", constraints=[_op("语气", "正式")])
    out = _classify(monkeypatch, proposal)
    assert out["core_intent"]["constraints"] == {"tone": "正式"}  # 语气归一为 tone


def test_unknown_constraint_key_retained(monkeypatch):
    """未知约束键保留原样,不丢弃。"""
    proposal = _proposal(change_type="init", goal="g", constraints=[_op("自定义维度", "某值")])
    out = _classify(monkeypatch, proposal)
    assert out["core_intent"]["constraints"] == {"自定义维度": "某值"}


def test_style_key_stays_independent(monkeypatch):
    """style 独立,不与 tone 合并。"""
    proposal = _proposal(
        change_type="init", goal="g",
        constraints=[_op("tone", "正式"), _op("风格", "文艺")],
    )
    out = _classify(monkeypatch, proposal)
    # 风格归一为 style,与 tone 独立共存
    assert out["core_intent"]["constraints"] == {"tone": "正式", "style": "文艺"}


def test_preference_task_dedup_constraints_win(monkeypatch):
    """偏好去重:scope=task 与 constraints 同 key 时 constraints 优先。"""
    from types import SimpleNamespace

    pref = SimpleNamespace(key="tone", value="轻松", scope="task")
    proposal = _proposal(
        change_type="append",
        constraints=[_op("tone", "正式")],  # 同 key
        preference=pref,
    )
    current = {"goal": "g", "constraints": {}, "acceptance_criteria": []}
    out = _classify(monkeypatch, proposal, state={"core_intent": current, "intent_version": 1})
    # constraints 优先,preference(scope=task)被忽略,结果只 tone=正式
    assert out["core_intent"]["constraints"] == {"tone": "正式"}
    assert "pending_preference" not in out  # task 偏好不入 pending


def test_preference_global_sets_pending(monkeypatch):
    """scope=global → 写 pending_preference(交由流中 upsert)。"""
    from types import SimpleNamespace

    pref = SimpleNamespace(key="language", value="英文", scope="global")
    proposal = _proposal(change_type="none", preference=pref, confidence=0.9)
    out = _classify(monkeypatch, proposal)
    assert out["pending_preference"] == {"key": "language", "value": "英文", "scope": "global"}


def test_preference_task_no_conflict_merged(monkeypatch):
    """scope=task 无同 key 冲突 → 并入 constraints。"""
    from types import SimpleNamespace

    pref = SimpleNamespace(key="length", value="简短", scope="task")
    proposal = _proposal(change_type="append", constraints=[_op("tone", "正式")], preference=pref)
    current = {"goal": "g", "constraints": {}, "acceptance_criteria": []}
    out = _classify(monkeypatch, proposal, state={"core_intent": current, "intent_version": 1})
    # length 并入 constraints,tone 也保留
    assert out["core_intent"]["constraints"] == {"tone": "正式", "length": "简短"}


# ---------- 任务 1.5:锚点 SystemMessage ----------

def test_render_anchor_stable_id():
    """render_anchor 产出稳定 id 的 SystemMessage。"""
    from app.services.agent.nodes import anchor_message_id, render_anchor

    core = {"goal": "g", "constraints": {"tone": "正式"}, "acceptance_criteria": []}
    msg = render_anchor(core, "s1")
    assert msg.id == anchor_message_id("s1") == "anchor:s1"
    assert "g" in msg.content
    assert "tone" in msg.content


def test_render_anchor_none_when_no_anchor():
    """无锚点不渲染。"""
    from app.services.agent.nodes import render_anchor

    assert render_anchor({}, "s1") is None
    assert render_anchor(None, "s1") is None


def test_sync_anchor_adds_when_missing():
    """锚点消息缺失 → 插入。"""
    from app.services.agent.nodes import _sync_anchor_message

    core = {"goal": "g", "constraints": {}, "acceptance_criteria": []}
    msgs = _sync_anchor_message({"session_id": "s1", "messages": []}, core)
    assert len(msgs) == 1
    assert getattr(msgs[0], "id", "") == "anchor:s1"


def test_sync_anchor_rebuilds_on_mismatch():
    """内容不一致 → 同 id RemoveMessage + add 新。"""
    from langchain_core.messages import SystemMessage

    from app.services.agent.nodes import _sync_anchor_message, render_anchor

    core = {"goal": "g", "constraints": {}, "acceptance_criteria": []}
    wrong = SystemMessage(content="旧锚点内容", id="anchor:s1")
    msgs = _sync_anchor_message({"session_id": "s1", "messages": [wrong]}, core)
    assert len(msgs) == 2
    assert msgs[0].id == "anchor:s1"  # RemoveMessage
    assert msgs[1].content == render_anchor(core, "s1").content


def test_sync_anchor_noop_when_match():
    """一致 → 无需变更。"""
    from app.services.agent.nodes import _sync_anchor_message, render_anchor

    core = {"goal": "g", "constraints": {}, "acceptance_criteria": []}
    expected = render_anchor(core, "s1")
    msgs = _sync_anchor_message({"session_id": "s1", "messages": [expected]}, core)
    assert msgs == []


def test_sync_anchor_removes_when_no_anchor():
    """无锚点但残留锚点消息 → 清理。"""
    from langchain_core.messages import SystemMessage

    from app.services.agent.nodes import _sync_anchor_message

    leftover = SystemMessage(content="旧锚点", id="anchor:s1")
    msgs = _sync_anchor_message({"session_id": "s1", "messages": [leftover]}, {})
    assert len(msgs) == 1
    assert msgs[0].id == "anchor:s1"  # RemoveMessage


def test_retained_window_preserves_anchor():
    """裁剪不裁锚点:锚点在保留区开头,移除区不含锚点。"""
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.services.agent.nodes import _is_anchor_message, _retained_window

    anchor = SystemMessage(content="锚点", id="anchor:s1")
    history = [anchor] + [HumanMessage(content=f"q{i}", id=f"q{i}") for i in range(10)]
    retained, removed = _retained_window(history, keep_count=3)
    assert retained[0] is anchor  # 锚点在保留区开头
    assert any(_is_anchor_message(m) for m in retained)
    assert not any(_is_anchor_message(m) for m in removed)  # 移除区不含锚点


def test_intent_classify_syncs_anchor_on_init(monkeypatch):
    """intent_classify 建锚时返回锚点消息更新。"""
    from app.services.agent.nodes import _is_anchor_message

    proposal = _proposal(change_type="init", goal="整理周报", constraints=[_op("tone", "正式")])
    out = _classify(monkeypatch, proposal, state={"session_id": "s1", "messages": []})
    assert "messages" in out
    anchors = [m for m in out["messages"] if _is_anchor_message(m)]
    assert len(anchors) == 1
    assert anchors[0].id == "anchor:s1"


def test_anchor_single_after_multiple_turns(monkeypatch):
    """30 轮(简化为多轮)后通道里只有一条锚点消息,不累积。"""
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph

    from app.services.agent.nodes import _is_anchor_message, intent_classify
    from app.services.agent.state import AgentState

    turn = {"i": 0}

    class FakeStructured:
        def invoke(self, msgs):
            turn["i"] += 1
            if turn["i"] == 1:
                return _proposal(change_type="init", goal="g", constraints=[_op("tone", "正式")])
            return _proposal(change_type="none")  # 后续轮不变更

    class FakeProvider:
        def with_structured_output(self, model):
            return FakeStructured()

    monkeypatch.setitem(intent_classify.__globals__, "get_deepseek_provider", lambda: FakeProvider())

    g = StateGraph(AgentState)
    g.add_node("intent_classify", intent_classify)
    g.add_edge(START, "intent_classify")
    g.add_edge("intent_classify", END)
    graph = g.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "s1"}}
    for i in range(8):
        list(
            graph.stream(
                {"question": f"q{i}", "session_id": "s1", "thoughts": [], "messages": []},
                config=config,
            )
        )
    snap = graph.get_state(config)
    anchors = [m for m in snap.values["messages"] if _is_anchor_message(m)]
    assert len(anchors) == 1  # 只有一条锚点


def test_best_answer_ignores_anchor():
    """_best_answer 不选锚点 SystemMessage。"""
    from langchain_core.messages import AIMessage, SystemMessage

    from app.services.agent.nodes import _best_answer

    anchor = SystemMessage(content="锚点很长的内容", id="anchor:s1")
    msgs = [
        SystemMessage(content="锚点很长的内容", id="anchor:s1"),
        AIMessage(content="本轮答案", id="a1"),
    ]
    # 锚点不是 AIMessage,不被选为答案
    assert _best_answer(msgs, "a1") == "本轮答案"
    assert "锚点" not in _best_answer(msgs, "a1")


# ---------- 任务 1.6:路由回写 + build_input 重置 + pending_preference 流中写入 ----------

def test_build_input_resets_temp_fields():
    """build_input 每轮重置临时字段;core_intent/intent_version 不重置(从 checkpoint 保留)。"""
    from app.services.agent.graph import build_input

    inp = build_input("q", "s1", "u1")
    assert inp["last_intent_change"] is None
    assert inp["low_confidence_hint"] == ""
    assert inp["pending_preference"] is None
    assert "core_intent" not in inp  # 锚点不在此重置
    assert "intent_version" not in inp


def test_persist_core_intent_writes_back(db):
    """终态回写:core_intent/intent_version/intent_versions 落 session。"""
    import json

    from app.api.routes.agent import _persist_core_intent
    from app.models.agent_session import AgentSession

    session = AgentSession(id="p1", user_id="u1", title="t")
    db.add(session)
    db.commit()
    db.refresh(session)
    values = {
        "core_intent": {"goal": "g", "constraints": {"tone": "正式"}, "acceptance_criteria": []},
        "intent_version": 2,
        "last_intent_change": {
            "change_type": "append", "source": "llm", "ts": "t",
            "confidence": 0.9, "unmapped_keys": [],
        },
    }
    _persist_core_intent(db, session, values)
    db.commit()
    db.refresh(session)
    assert json.loads(session.core_intent)["goal"] == "g"
    assert session.intent_version == 2
    versions = json.loads(session.intent_versions)
    assert versions[-1]["version"] == 2
    assert versions[-1]["change_type"] == "append"
    assert versions[-1]["confidence"] == 0.9


def test_persist_core_intent_skips_when_session_newer(db):
    """版本比较:checkpoint version < session version 时不覆盖。"""
    import json

    from app.api.routes.agent import _persist_core_intent
    from app.models.agent_session import AgentSession

    session = AgentSession(
        id="p2", user_id="u1", title="t",
        intent_version=5, core_intent=json.dumps({"goal": "旧"}),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    values = {
        "core_intent": {"goal": "新"}, "intent_version": 2,
        "last_intent_change": {"change_type": "append", "source": "llm", "ts": "t"},
    }
    _persist_core_intent(db, session, values)
    db.refresh(session)
    assert json.loads(session.core_intent)["goal"] == "旧"  # 不被旧 checkpoint 覆盖
    assert session.intent_version == 5


def test_persist_core_intent_dedup_last_version(db):
    """历史去重:末条 version == 当前则跳过,不重复追加。"""
    import json

    from app.api.routes.agent import _persist_core_intent
    from app.models.agent_session import AgentSession

    session = AgentSession(
        id="p3", user_id="u1", title="t",
        intent_version=2,
        intent_versions=json.dumps([{"version": 2, "change_type": "append"}]),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    values = {
        "core_intent": {"goal": "g"}, "intent_version": 2,
        "last_intent_change": {"change_type": "append", "source": "llm", "ts": "t"},
    }
    _persist_core_intent(db, session, values)
    db.commit()
    db.refresh(session)
    versions = json.loads(session.intent_versions)
    assert len(versions) == 1  # 去重,未重复追加(若未去重会变 2)


def test_stream_upserts_pending_preference_in_flight(monkeypatch, db):
    """pending_preference 流中写入:检测到立即 upsert,不等终态(断流不丢偏好)。"""
    import json
    from types import SimpleNamespace

    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph

    from app.api.routes import agent as agent_route
    from app.models.agent_session import AgentSession
    from app.services.agent.nodes import intent_classify
    from app.services.agent.state import AgentState

    upserted = {}

    def fake_upsert(db_sess, user_id, key, value, store=None):
        upserted["key"] = key
        upserted["value"] = value
        return SimpleNamespace(preference_key=key, preference_value=value)

    monkeypatch.setattr(agent_route, "upsert_preference", fake_upsert)

    pref = SimpleNamespace(key="language", value="英文", scope="global")
    proposal = _proposal(change_type="none", preference=pref)

    class FakeStructured:
        def invoke(self, msgs):
            return proposal

    class FakeProvider:
        def with_structured_output(self, model):
            return FakeStructured()

    monkeypatch.setitem(intent_classify.__globals__, "get_deepseek_provider", lambda: FakeProvider())

    g = StateGraph(AgentState)
    g.add_node("intent_classify", intent_classify)
    g.add_edge(START, "intent_classify")
    g.add_edge("intent_classify", END)
    compiled = g.compile(checkpointer=MemorySaver())
    monkeypatch.setattr(agent_route, "get_graph", lambda: compiled)

    session = AgentSession(id="sp1", user_id="u1", title="t")
    db.add(session)
    db.commit()
    db.refresh(session)

    graph_input = {
        "question": "q", "session_id": "sp1", "user_id": "u1", "thoughts": [],
        "messages": [], "last_intent_change": None, "low_confidence_hint": "",
        "pending_preference": None,
    }
    list(
        agent_route._stream_graph(
            db, graph_input, session, "u1",
            config={"configurable": {"thread_id": "sp1"}},
            in_flight_thread_id=None,
        )
    )
    assert upserted.get("key") == "language"
    assert upserted.get("value") == "英文"


# ---------- 任务 1.7:CORE_INTENT_ENABLED 三模式 ----------

def _set_mode(monkeypatch, mode):
    from app.services.agent.nodes import intent_classify

    monkeypatch.setitem(intent_classify.__globals__, "CORE_INTENT_ENABLED", mode)


def test_off_mode_no_anchor_write(monkeypatch):
    """off:不计算锚点,不写 core_intent,不注入锚点消息。"""
    _set_mode(monkeypatch, "off")
    proposal = _proposal(change_type="init", goal="不该生效", constraints=[_op("tone", "正式")])
    out = _classify(monkeypatch, proposal, state={"session_id": "s1", "messages": []})
    assert "core_intent" not in out
    assert "intent_version" not in out
    assert "messages" not in out  # off 不注入锚点


def test_off_mode_cleans_anchor_messages(monkeypatch):
    """off:清理残留锚点消息。"""
    from langchain_core.messages import SystemMessage

    from app.services.agent.nodes import anchor_message_id

    _set_mode(monkeypatch, "off")
    leftover = SystemMessage(content="旧锚点", id=anchor_message_id("s1"))
    proposal = _proposal(change_type="none")
    out = _classify(monkeypatch, proposal, state={"session_id": "s1", "messages": [leftover]})
    assert "messages" in out
    assert any(getattr(m, "id", "") == anchor_message_id("s1") for m in out["messages"])  # RemoveMessage


def test_shadow_mode_compute_no_write(monkeypatch):
    """shadow:只算不写 state、不注入锚点。"""
    _set_mode(monkeypatch, "shadow")
    proposal = _proposal(change_type="init", goal="g", constraints=[_op("tone", "正式")])
    out = _classify(monkeypatch, proposal, state={"session_id": "s1", "messages": []})
    assert "core_intent" not in out  # 不写 state
    assert "intent_version" not in out
    assert "messages" not in out  # 不注入锚点


def test_on_mode_writes_and_injects(monkeypatch):
    """on:写 state + 注入锚点(默认模式)。"""
    _set_mode(monkeypatch, "on")
    proposal = _proposal(change_type="init", goal="g", constraints=[_op("tone", "正式")])
    out = _classify(monkeypatch, proposal, state={"session_id": "s1", "messages": []})
    assert out["core_intent"]["goal"] == "g"
    assert out["intent_version"] == 1
    assert "messages" in out  # 注入锚点


def test_off_to_on_revives_anchor(monkeypatch):
    """off 切回 on:state 保留的旧锚点复活(重新注入锚点消息)。"""
    from app.services.agent.nodes import _is_anchor_message

    current = {"goal": "旧目标", "constraints": {}, "acceptance_criteria": []}
    _set_mode(monkeypatch, "on")
    proposal = _proposal(change_type="none")
    out = _classify(
        monkeypatch, proposal,
        state={"session_id": "s1", "messages": [], "core_intent": current, "intent_version": 1},
    )
    assert "messages" in out
    anchors = [m for m in out["messages"] if _is_anchor_message(m)]
    assert len(anchors) == 1  # 锚点复活
    assert "旧目标" in anchors[0].content


def test_core_intent_summary_and_full_helpers(db):
    """/sessions 摘要(goal 截断 80 + version)与 /messages 完整 core_intent。"""
    import json

    from app.api.routes.agent import _core_intent_full, _core_intent_summary
    from app.models.agent_session import AgentSession

    session = AgentSession(
        id="e1", user_id="u1", title="t", intent_version=2,
        core_intent=json.dumps(
            {"goal": "整理周报" * 30, "constraints": {"tone": "正式"}, "acceptance_criteria": []},
            ensure_ascii=False,
        ),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    summary = _core_intent_summary(db, session)
    assert summary["version"] == 2
    assert len(summary["goal"]) <= 80  # 截断
    full = _core_intent_full(db, session)
    assert full["constraints"] == {"tone": "正式"}
    assert full["goal"] == "整理周报" * 30  # 完整不截断


# ---------- 任务 1.8:/resume 合并 ----------

def test_extract_resume_changes_constraint():
    """审批理由"把X改成Y" → 约束。"""
    from app.services.agent.nodes import _extract_resume_changes

    out = _extract_resume_changes("批准,但把标题改成周报汇总")
    assert len(out["constraints"]) == 1
    assert out["constraints"][0].key == "标题"
    assert out["constraints"][0].value == "周报汇总"
    assert out["preference"] is None


def test_extract_resume_changes_preference_global():
    """审批理由"以后都用英文" → global 偏好。"""
    from app.services.agent.nodes import _extract_resume_changes

    out = _extract_resume_changes("批准,以后都用英文")
    assert out["preference"] is not None
    assert out["preference"]["scope"] == "global"
    assert out["preference"]["key"] == "language"
    assert out["preference"]["value"] == "英文"


def test_extract_resume_changes_empty():
    """理由为空/仅批准 → 无约束无偏好。"""
    from app.services.agent.nodes import _extract_resume_changes

    out = _extract_resume_changes("批准")
    assert out["constraints"] == []
    assert out["preference"] is None


def test_apply_resume_merge_appends_and_bumps(monkeypatch):
    """resume 当成 append:合并约束,bump version,source=resume。"""
    from app.services.agent.nodes import _apply_resume_merge

    current = {"goal": "g", "constraints": {"tone": "正式"}, "acceptance_criteria": []}
    constraints = [_op("length", "简短")]
    change = _apply_resume_merge(current, 1, constraints, None)
    assert change is not None
    new_anchor, new_version, applied_ct, source = change
    assert new_anchor["constraints"] == {"tone": "正式", "length": "简短"}
    assert new_version == 2
    assert applied_ct == "append"
    assert source == "resume"


def test_apply_resume_merge_no_constraints_returns_none():
    """无约束变更(仅 global 偏好)→ 不 bump 版本,返回 None(偏好单独 upsert)。"""
    from app.services.agent.nodes import _apply_resume_merge

    current = {"goal": "g", "constraints": {}, "acceptance_criteria": []}
    pref = {"key": "language", "value": "英文", "scope": "global"}
    change = _apply_resume_merge(current, 1, [], pref)
    assert change is None  # global 偏好不并入锚点


# ---------- 任务 1.9:低置信提示 + 偏好提取 ----------

def test_output_appends_low_confidence_hint():
    """output 把 low_confidence_hint 拼接到 answer 末尾(模型下一轮看不到,用户需重述)。"""
    from langchain_core.messages import AIMessage, HumanMessage

    from app.services.agent.nodes import output

    state = {
        "messages": [HumanMessage(content="q", id="q1"), AIMessage(content="本轮答案", id="a1")],
        "turn_start_id": "q1",
        "low_confidence_hint": "(置信度较低,拟将语气改为正式,请重新完整表达以确认)",
    }
    out = output(state)
    assert "本轮答案" in out["answer"]
    assert "请重新完整表达以确认" in out["answer"]  # 提示在 answer 末尾
    assert out["answer"].endswith("请重新完整表达以确认)")


def test_output_no_hint_answer_unchanged():
    """无 hint 时答案不变。"""
    from langchain_core.messages import AIMessage, HumanMessage

    from app.services.agent.nodes import output

    state = {
        "messages": [HumanMessage(content="q", id="q1"), AIMessage(content="本轮答案", id="a1")],
        "turn_start_id": "q1",
        "low_confidence_hint": "",
    }
    out = output(state)
    assert out["answer"] == "本轮答案"


def test_output_hint_not_injected_into_messages():
    """低置信提示只进 answer,不进 messages(模型下一轮看不到)。"""
    from langchain_core.messages import AIMessage, HumanMessage

    from app.services.agent.nodes import output

    state = {
        "messages": [HumanMessage(content="q", id="q1"), AIMessage(content="本轮答案", id="a1")],
        "turn_start_id": "q1",
        "low_confidence_hint": "(置信度较低,拟变更提示)",
    }
    out = output(state)
    # output 不返回 messages,提示不注入消息通道
    assert "messages" not in out
    assert "拟变更提示" in out["answer"]


def test_intent_classify_low_confidence_writes_hint_field(monkeypatch):
    """低置信时 intent_classify 写 low_confidence_hint state 字段(不写 messages)。"""
    proposal = _proposal(change_type="append", constraints=[_op("tone", "轻松")], confidence=0.2)
    current = {"goal": "g", "constraints": {"tone": "正式"}, "acceptance_criteria": []}
    out = _classify(monkeypatch, proposal, state={"core_intent": current, "intent_version": 1, "session_id": "s1", "messages": []})
    assert out["low_confidence_hint"]  # 写了提示字段
    assert "messages" not in out or not any(
        "轻松" in (getattr(m, "content", "") or "") for m in out.get("messages", [])
    )  # 提示不在消息里
