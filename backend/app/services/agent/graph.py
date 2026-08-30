import os
import sqlite3
from typing import Any, Dict, List, Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.services.agent.config import CHECKPOINT_DB, MULTI_AGENT
from app.services.agent.memory import get_memory_store
from app.services.agent.nodes import (
    agent_step,
    answer_quality,
    direct_answer,
    execute_tool,
    generate,
    grade_documents,
    hallucination_check,
    intent_classify,
    output,
    rewrite_question,
    route_answer_quality,
    route_grade_documents,
    route_hallucination,
    route_intent,
    route_intent_multi,
    should_continue,
)
from app.services.agent.state import AgentState

_graph = None
_multi_graph = None
_checkpointer = None


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("agent_step", agent_step)
    g.add_node("execute_tool", execute_tool)
    g.add_node("grade_documents", grade_documents)
    g.add_node("rewrite_question", rewrite_question)
    g.add_node("generate", generate)
    g.add_node("hallucination_check", hallucination_check)
    g.add_node("answer_quality", answer_quality)
    g.add_node("intent_classify", intent_classify)
    g.add_node("direct_answer", direct_answer)
    g.add_node("output", output)

    g.add_edge(START, "intent_classify")
    g.add_conditional_edges(
        "intent_classify",
        route_intent,
        {"agent_step": "agent_step", "direct_answer": "direct_answer"},
    )
    g.add_edge("direct_answer", "output")
    g.add_conditional_edges(
        "agent_step",
        should_continue,
        {
            "execute_tool": "execute_tool",
            "grade_documents": "grade_documents",
            "generate": "generate",  # M7.3:web_research 跳过文档评级直达 generate
            "output": "output",
        },
    )
    g.add_edge("execute_tool", "agent_step")
    g.add_conditional_edges(
        "grade_documents",
        route_grade_documents,
        {"generate": "generate", "rewrite_question": "rewrite_question"},
    )
    g.add_edge("rewrite_question", "agent_step")
    g.add_edge("generate", "hallucination_check")
    g.add_conditional_edges(
        "hallucination_check",
        route_hallucination,
        {"answer_quality": "answer_quality", "output": "output", "rewrite_question": "rewrite_question"},
    )
    g.add_conditional_edges(
        "answer_quality",
        route_answer_quality,
        {"output": "output", "rewrite_question": "rewrite_question"},
    )
    g.add_edge("output", END)
    return g


def build_multi_agent_graph():
    """M7 A′ 平铺图:节点与单 Agent 图完全复用,差异仅在路由语义——
    条件边按 4 个 agent 名分发(chat_agent 复用 direct_answer 节点,
    knowledge/web_research/note_write 复用 agent_step),工具与提示词由
    nodes.AGENT_CONFIGS 按 current_agent 查表决定。
    spike(M7.0)阶段各 agent 配置相同,行为与单 Agent 图一致;M7.1+ 在此图上差异化。"""
    g = StateGraph(AgentState)
    g.add_node("agent_step", agent_step)
    g.add_node("execute_tool", execute_tool)
    g.add_node("grade_documents", grade_documents)
    g.add_node("rewrite_question", rewrite_question)
    g.add_node("generate", generate)
    g.add_node("hallucination_check", hallucination_check)
    g.add_node("answer_quality", answer_quality)
    g.add_node("intent_classify", intent_classify)
    g.add_node("direct_answer", direct_answer)
    g.add_node("output", output)

    g.add_edge(START, "intent_classify")
    g.add_conditional_edges(
        "intent_classify",
        route_intent_multi,
        {
            "chat_agent": "direct_answer",
            "knowledge_agent": "agent_step",
            "web_research_agent": "agent_step",
            "note_write_agent": "agent_step",
        },
    )
    g.add_edge("direct_answer", "output")
    g.add_conditional_edges(
        "agent_step",
        should_continue,
        {
            "execute_tool": "execute_tool",
            "grade_documents": "grade_documents",
            "generate": "generate",  # M7.3:web_research 跳过文档评级直达 generate
            "output": "output",
        },
    )
    g.add_edge("execute_tool", "agent_step")
    g.add_conditional_edges(
        "grade_documents",
        route_grade_documents,
        {"generate": "generate", "rewrite_question": "rewrite_question"},
    )
    g.add_edge("rewrite_question", "agent_step")
    g.add_edge("generate", "hallucination_check")
    g.add_conditional_edges(
        "hallucination_check",
        route_hallucination,
        {"answer_quality": "answer_quality", "output": "output", "rewrite_question": "rewrite_question"},
    )
    g.add_conditional_edges(
        "answer_quality",
        route_answer_quality,
        {"output": "output", "rewrite_question": "rewrite_question"},
    )
    g.add_edge("output", END)
    return g


def _create_checkpointer() -> SqliteSaver:
    os.makedirs(os.path.dirname(os.path.abspath(CHECKPOINT_DB)), exist_ok=True)
    conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
    return SqliteSaver(conn)


def get_checkpointer() -> SqliteSaver:
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = _create_checkpointer()
    return _checkpointer


def get_graph():
    """按 AGENT_MULTI_AGENT 旗标返回多 Agent 图(A′)或单 Agent 图(回退位)。
    双图共存:回滚改 .env 即可,无需重新部署;eval 可同进程对比新旧图。"""
    global _graph, _multi_graph
    if MULTI_AGENT:
        if _multi_graph is None:
            _multi_graph = build_multi_agent_graph().compile(
                checkpointer=get_checkpointer(),
                store=get_memory_store(),
            )
        return _multi_graph
    if _graph is None:
        _graph = build_graph().compile(
            checkpointer=get_checkpointer(),
            store=get_memory_store(),
        )
    return _graph


def delete_thread(thread_id: str) -> None:
    get_checkpointer().delete_thread(thread_id)


def build_input(question: str, session_id: str, user_id: str, history: Optional[List[dict]] = None) -> Dict[str, Any]:
    """构造图的初始输入。history 为 [{role, content}] 的会话内历史。"""
    msgs = []
    if history:
        for h in history:
            role = h.get("role")
            content = h.get("content") or ""
            if role == "user":
                msgs.append({"role": "user", "content": content})
            elif role == "assistant":
                msgs.append({"role": "assistant", "content": content})
    msgs.append({"role": "user", "content": question})
    return {
        "messages": msgs,
        "question": question,
        "session_id": session_id,
        "user_id": user_id,
        "iteration": 0,
        "token_used": 0,
        "documents": [],
        "thoughts": [],
        "tool_calls_log": [],
        "searched_queries": [],
    }
