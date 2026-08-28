import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.agent import _pending_approval_payload
from app.db.base import Base
from app.models.agent_session import AgentSession, AgentToolCall
from app.models.user import User
from app.services.agent.memory import (
    delete_preference,
    list_preferences,
    preference_namespace,
    upsert_preference,
)
from app.services.agent.nodes import _retained_window, execute_tool
from app.services.agent.state import AgentState
from app.services.observability import trace_service
from app.services.observability.trace_service import (
    list_local_traces,
    list_traces,
    observability_summary,
)


def make_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_user(db, user_id="user-1"):
    user = User(id=user_id, username=f"name-{user_id}", password_hash="hash")
    db.add(user)
    db.commit()
    return user


def test_preferences_are_durable_and_synced_to_store():
    db = make_db()
    user = make_user(db)
    store = InMemoryStore()

    row = upsert_preference(db, user.id, "answer_style", "先给结论", store)

    assert row.preference_value == "先给结论"
    assert list_preferences(db, user.id) == {"answer_style": "先给结论"}
    assert store.get(preference_namespace(user.id), "answer_style").value == {"value": "先给结论"}

    assert delete_preference(db, user.id, "answer_style", store) is True
    assert list_preferences(db, user.id) == {}
    assert store.get(preference_namespace(user.id), "answer_style") is None
    db.close()


def _hitl_graph():
    builder = StateGraph(AgentState)
    builder.add_node("execute_tool", execute_tool)
    builder.add_edge(START, "execute_tool")
    builder.add_edge("execute_tool", END)
    return builder.compile(checkpointer=MemorySaver())


def _hitl_input():
    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_note",
                        "args": {"title": "审批测试", "content": "只有批准后才写入"},
                        "id": "call-create-note",
                        "type": "tool_call",
                    }
                ],
            )
        ],
        "thoughts": [],
        "tool_calls_log": [],
        "documents": [],
    }


def test_hitl_interrupt_rejects_without_executing(monkeypatch):
    calls = []

    class FakeCreateNote:
        def invoke(self, args):
            calls.append(args)
            return json.dumps({"id": "new-note"})

    monkeypatch.setitem(execute_tool.__globals__["TOOL_MAP"], "create_note", FakeCreateNote())
    graph = _hitl_graph()
    config = {"configurable": {"thread_id": "reject-thread"}}

    first = list(graph.stream(_hitl_input(), config=config))
    assert first[-1]["__interrupt__"][0].value["tool_name"] == "create_note"
    assert calls == []

    resumed = list(graph.stream(Command(resume={"approved": False, "reason": "不需要"}), config=config))
    update = resumed[-1]["execute_tool"]
    assert calls == []
    assert update["tool_calls_log"][-1]["status"] == "rejected"


def test_hitl_executes_once_after_approval(monkeypatch):
    calls = []

    class FakeCreateNote:
        def invoke(self, args):
            calls.append(args)
            return json.dumps({"id": "new-note", "title": args["title"]})

    monkeypatch.setitem(execute_tool.__globals__["TOOL_MAP"], "create_note", FakeCreateNote())
    graph = _hitl_graph()
    config = {"configurable": {"thread_id": "approve-thread"}}

    list(graph.stream(_hitl_input(), config=config))
    resumed = list(graph.stream(Command(resume={"approved": True}), config=config))
    update = resumed[-1]["execute_tool"]

    assert len(calls) == 1
    assert calls[0]["title"] == "审批测试"
    assert update["tool_calls_log"][-1]["status"] == "success"
    assert update["tool_calls_log"][-1]["latency_ms"] >= 0


def test_local_observability_aggregates_calls():
    db = make_db()
    user = make_user(db)
    session = AgentSession(id="session-1", user_id=user.id, title="可观测测试")
    db.add(session)
    db.add_all(
        [
            AgentToolCall(
                session_id=session.id,
                tool_name="search_notes",
                args_json="{}",
                result_json="[]",
                latency_ms=120,
                status="success",
            ),
            AgentToolCall(
                session_id=session.id,
                tool_name="create_note",
                args_json="{}",
                result_json="{}",
                latency_ms=80,
                status="pending",
            ),
        ]
    )
    db.commit()

    summary = observability_summary(db, user.id)
    traces = list_local_traces(db, user.id)

    assert summary["sessions"] == 1
    assert summary["tool_calls"] == 2
    assert summary["avg_tool_latency_ms"] == 100
    assert summary["pending_approvals"] == 1
    assert traces["data"][0]["status"] == "pending"
    assert traces["data"][0]["latency_ms"] == 200
    db.close()


def test_auto_trace_source_falls_back_when_langfuse_fails(monkeypatch):
    db = make_db()
    user = make_user(db)
    db.add(AgentSession(id="session-fallback", user_id=user.id, title="fallback"))
    db.commit()

    monkeypatch.setattr(trace_service, "langfuse_configured", lambda: True)
    monkeypatch.setattr(
        trace_service,
        "list_langfuse_traces",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("cloud unavailable")),
    )

    result = list_traces(db, user.id, source="auto")
    assert result["source"] == "local"
    assert "cloud unavailable" in result["fallback_reason"]
    db.close()


def test_retained_window_preserves_tool_pair():
    """裁剪点落在 tool_calls 配对中间时，保留区应向前扩展到配对的 AIMessage。"""
    # 构造 30 条：index 0=H，之后 10 组 [A(tool_calls), T]，索引 1+2i=A(ci)、2+2i=T(ci)
    paired: list = [HumanMessage(content="q0")]
    for i in range(10):
        paired.append(
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "search_notes", "args": {"query": str(i)}, "id": f"c{i}", "type": "tool_call"}
                ],
            )
        )
        paired.append(ToolMessage(content="r", tool_call_id=f"c{i}"))
    while len(paired) < 30:
        paired.append(HumanMessage(content="pad"))
    assert len(paired) == 30

    # start=30-22=8 → paired[8] 是 ToolMessage(c3)，应回退到配对的 AIMessage(c3) (index 7)
    retained, removed = _retained_window(paired, 22)
    assert not isinstance(retained[0], ToolMessage)
    assert retained[0].tool_calls and retained[0].tool_calls[0]["id"] == "c3"
    assert removed + retained == paired

    # 裁剪起点不落在配对中时行为与机械裁剪一致
    plain = [HumanMessage(content=f"q{i}") for i in range(30)]
    retained_plain, removed_plain = _retained_window(plain, 23)
    assert len(retained_plain) == 23
    assert len(removed_plain) == 7


def test_pending_approval_roundtrip():
    """interrupt 挂起时可从 snapshot 恢复审批 payload，resume 后提取为 None。"""
    graph = _hitl_graph()
    config = {"configurable": {"thread_id": "restore-thread"}}

    list(graph.stream(_hitl_input(), config=config))
    snapshot = graph.get_state(config)
    assert snapshot.next

    payload = _pending_approval_payload(snapshot, "restore-thread")
    assert payload is not None
    assert payload["type"] == "approval_required"
    assert payload["tool_name"] == "create_note"
    assert payload["session_id"] == "restore-thread"

    list(graph.stream(Command(resume={"approved": False, "reason": "不需要"}), config=config))
    assert _pending_approval_payload(graph.get_state(config), "restore-thread") is None
