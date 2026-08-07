import json
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.services.agent.config import MAX_ITERATIONS, TOKEN_BUDGET
from app.services.agent.prompts import (
    GRADE_ANSWER_PROMPT,
    GRADE_DOCUMENTS_PROMPT,
    GRADE_HALLUCINATIONS_PROMPT,
    REACT_SYSTEM_PROMPT,
    GradeAnswer,
    GradeDocuments,
    GradeHallucinations,
)
from app.services.agent.state import AgentState
from app.services.llm.deepseek_provider import get_deepseek_provider
from app.services.tools import (
    get_graph_neighbors,
    get_note,
    list_folders,
    list_tags,
    search_notes,
    web_search,
)

ALL_TOOLS = [search_notes, get_note, get_graph_neighbors, list_tags, list_folders, web_search]
TOOL_MAP = {t.name: t for t in ALL_TOOLS}


def _doc_text(docs: List[dict], limit: int = 5) -> str:
    lines = []
    for d in docs[:limit]:
        snippet = (d.get("snippet") or "")[:200]
        lines.append(f"- 《{d.get('title', '')}》: {snippet}")
    return "\n".join(lines) if lines else "(无)"


def _append_thought(state: AgentState, entry: dict) -> List[dict]:
    thoughts = list(state.get("thoughts") or [])
    thoughts.append(entry)
    return thoughts


# ---------- 节点 ----------
def agent_step(state: AgentState) -> Dict[str, Any]:
    provider = get_deepseek_provider()
    llm = provider.bind_tools(ALL_TOOLS)
    msgs: List[Any] = [SystemMessage(content=REACT_SYSTEM_PROMPT)]
    msgs.extend(state.get("messages") or [])
    resp = llm.invoke(msgs)

    iteration = (state.get("iteration") or 0) + 1
    usage = getattr(resp, "usage_metadata", None) or {}
    token_used = (state.get("token_used") or 0) + (usage.get("total_tokens") or 0)

    return {
        "messages": [resp],
        "iteration": iteration,
        "token_used": token_used,
        "thoughts": _append_thought(state, {"type": "thought", "content": resp.content or ""}),
    }


def execute_tool(state: AgentState) -> Dict[str, Any]:
    last = state["messages"][-1]
    tool_calls = getattr(last, "tool_calls", None) or []
    thoughts = _append_thought(state, {"type": "action", "content": "执行工具"})
    tool_log = list(state.get("tool_calls_log") or [])
    documents = list(state.get("documents") or [])
    new_msgs: List[Any] = []

    for tc in tool_calls:
        name = tc.get("name", "")
        args = tc.get("args", {}) or {}
        fn = TOOL_MAP.get(name)
        try:
            result = fn.invoke(args) if fn else f"未知工具:{name}"
        except Exception as e:
            result = f"工具执行出错:{e}"

        new_msgs.append(ToolMessage(content=result, tool_call_id=tc.get("id", "")))
        thoughts.append({"type": "action", "content": f"{name}{json.dumps(args, ensure_ascii=False)}"})
        thoughts.append({"type": "observation", "content": result[:300]})
        tool_log.append({"tool": name, "args": args, "result": result[:500]})

        if name == "search_notes":
            try:
                docs = json.loads(result)
                if isinstance(docs, list):
                    documents.extend(docs)
            except Exception:
                pass

    return {
        "messages": new_msgs,
        "thoughts": thoughts,
        "tool_calls_log": tool_log,
        "documents": documents,
    }


def grade_documents(state: AgentState) -> Dict[str, Any]:
    docs = state.get("documents") or []
    thoughts = _append_thought(state, {"type": "check", "content": "grade_documents: 开始"})
    if not docs:
        thoughts.append({"type": "check", "content": "grade_documents: 无检索文档,放行"})
        return {"grade_documents": "yes", "thoughts": thoughts}

    provider = get_deepseek_provider()
    structured = provider.with_structured_output(GradeDocuments)
    resp = structured.invoke(
        [
            SystemMessage(content=GRADE_DOCUMENTS_PROMPT),
            HumanMessage(content=f"问题:{state['question']}\n\n文档:\n{_doc_text(docs)}"),
        ]
    )
    score = (resp.binary_score or "").lower()
    thoughts.append({"type": "check", "content": f"grade_documents: {score} ({resp.reason})"})
    return {"documents_grade": score, "thoughts": thoughts}


def generate(state: AgentState) -> Dict[str, Any]:
    answer = ""
    for m in reversed(state.get("messages") or []):
        if isinstance(m, AIMessage):
            answer = m.content or ""
            break
    return {"answer": answer}


def hallucination_check(state: AgentState) -> Dict[str, Any]:
    answer = state.get("answer") or ""
    docs = state.get("documents") or []
    thoughts = _append_thought(state, {"type": "check", "content": "hallucination_check: 开始"})
    if not docs:
        thoughts.append({"type": "check", "content": "hallucination_check: 无文档可核对,放行"})
        return {"hallucination_ok": "yes", "thoughts": thoughts}

    provider = get_deepseek_provider()
    structured = provider.with_structured_output(GradeHallucinations)
    resp = structured.invoke(
        [
            SystemMessage(content=GRADE_HALLUCINATIONS_PROMPT),
            HumanMessage(content=f"答案:\n{answer}\n\n检索证据:\n{_doc_text(docs)}"),
        ]
    )
    score = (resp.binary_score or "").lower()
    thoughts.append({"type": "check", "content": f"hallucination_check: {score} ({resp.reason})"})
    return {"hallucination_ok": score, "thoughts": thoughts}


def answer_quality(state: AgentState) -> Dict[str, Any]:
    answer = state.get("answer") or ""
    thoughts = _append_thought(state, {"type": "check", "content": "answer_quality: 开始"})

    provider = get_deepseek_provider()
    structured = provider.with_structured_output(GradeAnswer)
    resp = structured.invoke(
        [
            SystemMessage(content=GRADE_ANSWER_PROMPT),
            HumanMessage(content=f"用户问题:{state['question']}\n\n模型答案:\n{answer}"),
        ]
    )
    score = (resp.binary_score or "").lower()
    thoughts.append({"type": "check", "content": f"answer_quality: {score} ({resp.reason})"})
    return {"answer_ok": score, "thoughts": thoughts}


def rewrite_question(state: AgentState) -> Dict[str, Any]:
    provider = get_deepseek_provider()
    resp = provider.get_chat_model().invoke(
        f"把下面的问题改写成更适合知识库检索的查询(保留原意,可拆成多个关键词):\n{state['question']}"
    )
    new_q = (resp.content or "").strip()
    thoughts = _append_thought(state, {"type": "thought", "content": f"改写问题: {state['question']} -> {new_q}"})
    return {"question": new_q, "thoughts": thoughts}


def output(state: AgentState) -> Dict[str, Any]:
    answer = state.get("answer")
    if not answer:
        for m in reversed(state.get("messages") or []):
            if isinstance(m, AIMessage):
                answer = m.content or ""
                break
    if not answer:
        answer = "已达到最大迭代次数,未能生成满意答案。"
    return {"answer": answer}


# ---------- 路由 ----------
def should_continue(state: AgentState) -> str:
    if (state.get("iteration") or 0) >= MAX_ITERATIONS:
        return "output"
    if (state.get("token_used") or 0) >= TOKEN_BUDGET:
        return "output"
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "execute_tool"
    return "grade_documents"


def route_grade_documents(state: AgentState) -> str:
    return "generate" if state.get("documents_grade") != "no" else "rewrite_question"


def route_hallucination(state: AgentState) -> str:
    return "answer_quality" if state.get("hallucination_ok") != "no" else "rewrite_question"


def route_answer_quality(state: AgentState) -> str:
    return "output" if state.get("answer_ok") != "no" else "rewrite_question"
