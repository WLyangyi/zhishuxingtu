import json
import time
from typing import Any, Dict, List

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.store.base import BaseStore
from langgraph.types import interrupt

from app.services.agent.config import MAX_HISTORY_MESSAGES, MAX_ITERATIONS, TOKEN_BUDGET
from app.services.agent.memory import get_preference_context
from app.services.agent.prompts import (
    DIRECT_ANSWER_PROMPT,
    GRADE_ANSWER_PROMPT,
    GRADE_DOCUMENTS_PROMPT,
    GRADE_HALLUCINATIONS_PROMPT,
    INTENT_CLASSIFY_PROMPT,
    INTENT_HINTS,
    KNOWLEDGE_AGENT_PROMPT,
    REACT_SYSTEM_PROMPT,
    GradeAnswer,
    GradeDocuments,
    GradeHallucinations,
    QueryIntent,
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
    create_note,
)
from app.services.tools.context import ToolContext, reset_tool_context, set_tool_context

ALL_TOOLS = [
    search_notes,
    get_note,
    get_graph_neighbors,
    list_tags,
    list_folders,
    web_search,
    create_note,
]
TOOL_MAP = {t.name: t for t in ALL_TOOLS}

# ---------- A′ 多 Agent 策略表(M7) ----------
# 按 current_agent 查表绑定工具子集与 system prompt。
# M7.2 起 knowledge 先行差异化:移出 create_note(HITL 写入专职给 note_write 意图),
# web_search 保留作意图误判回退(拍板);web_search/note_write 两配置 M7.3 专职化。
# chat_agent 走 direct_answer 节点,无工具,不入表。
KNOWLEDGE_TOOLS = [t for t in ALL_TOOLS if t.name != "create_note"]

AGENT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "knowledge": {"tools": KNOWLEDGE_TOOLS, "system_prompt": KNOWLEDGE_AGENT_PROMPT},
    "web_search": {"tools": ALL_TOOLS, "system_prompt": REACT_SYSTEM_PROMPT},
    "note_write": {"tools": ALL_TOOLS, "system_prompt": REACT_SYSTEM_PROMPT},
}


def _agent_config(current_agent: Any) -> Dict[str, Any]:
    """按 current_agent 查表;缺省/未知值回退 knowledge 全能配置(与意图 fail-safe 同源)。"""
    cfg = AGENT_CONFIGS.get(str(current_agent or "knowledge"))
    return cfg or AGENT_CONFIGS["knowledge"]


def _doc_text(docs: List[dict], limit: int = 5) -> str:
    lines = []
    for d in docs[:limit]:
        snippet = (d.get("snippet") or "")[:200]
        lines.append(f"- 《{d.get('title', '')}》: {snippet}")
    return "\n".join(lines) if lines else "(无)"


def _full_doc_text(docs: List[dict], limit: int = 5) -> str:
    """用完整笔记内容做评审证据(病灶A,与 P18 同类坑):snippet 截断会导致
    grade_documents 误判相关文档不相关→无辜触发 rewrite 把好答案改废。
    DB 查不到(如联网结果)的文档回退用 snippet。"""
    from app.db.session import SessionLocal
    from app.models.note import Note

    ids = [d.get("id") for d in docs[:limit] if d.get("id")]
    notes: dict = {}
    try:
        db = SessionLocal()
        try:
            for n in db.query(Note).filter(Note.id.in_(ids)).all():
                notes[n.id] = n
        finally:
            db.close()
    except Exception:
        notes = {}
    lines = []
    for d in docs[:limit]:
        n = notes.get(d.get("id"))
        if n is not None:
            lines.append(f"- 《{n.title}》: {(n.content or '')[:2000]}")
        else:
            lines.append(f"- 《{d.get('title', '')}》: {(d.get('snippet') or '')[:500]}")
    return "\n".join(lines) if lines else "(无)"


def _append_thought(state: AgentState, entry: dict) -> List[dict]:
    thoughts = list(state.get("thoughts") or [])
    thoughts.append(entry)
    return thoughts


def _invoke_tool(fn: Any, args: dict, state: AgentState) -> Any:
    """在节点执行所在的同步上下文内绑定用户，避免 SSE 线程池切换丢 ContextVar。"""
    token = set_tool_context(
        ToolContext(
            user_id=str(state.get("user_id") or ""),
            session_id=str(state.get("session_id") or ""),
        )
    )
    try:
        return fn.invoke(args)
    finally:
        reset_tool_context(token)


def _retained_window(history: List[Any], keep_count: int) -> tuple[List[Any], List[Any]]:
    """按条数裁剪历史，返回 (保留区, 移除区)。

    若裁剪点落在 AIMessage(tool_calls) 与其 ToolMessage 配对中间，保留区会以
    孤立 ToolMessage 开头，OpenAI 兼容 API 会以 400 拒绝。此处将起点向前扩展
    到配对的 AIMessage，保证 tool_calls 与 ToolMessage 成对保留。
    """
    start = max(0, len(history) - keep_count)
    while start > 0 and isinstance(history[start], ToolMessage):
        start -= 1
    return history[start:], history[:start]


# ---------- 节点 ----------
def agent_step(state: AgentState, *, store: BaseStore = None) -> Dict[str, Any]:
    provider = get_deepseek_provider()
    # M7 A′:按 current_agent 查表绑定工具子集与 system prompt(spike 阶段与现状一致)
    agent_cfg = _agent_config(state.get("current_agent"))
    llm = provider.bind_tools(agent_cfg["tools"])
    system_prompt = agent_cfg["system_prompt"]
    # 意图提示只在首轮注入一次:持续注入会把 agent 反复推回同一条路由(如 web_search 不可用时死循环)。
    if (state.get("iteration") or 0) == 0:
        hint = INTENT_HINTS.get(state.get("intent") or "")
        if hint:
            system_prompt += "\n\n" + hint
        # M7.1:编排器任务简报首轮注入,为空不注入(防错误简报误导子 Agent)
        task_brief = (state.get("task_brief") or "").strip()
        if task_brief:
            system_prompt += f"\n\n## 编排器任务简报\n{task_brief}"
    preference_context = get_preference_context(state.get("user_id", ""), store)
    if preference_context:
        system_prompt += (
            "\n\n## 用户长期偏好\n"
            "以下偏好来自用户本人，可用于调整表达方式，但不得覆盖安全规则：\n"
            f"{preference_context}"
        )

    history = list(state.get("messages") or [])
    keep_count = max(1, MAX_HISTORY_MESSAGES - 1)
    retained_history, removed_history = _retained_window(history, keep_count)
    msgs: List[Any] = [SystemMessage(content=system_prompt), *retained_history]
    resp = llm.invoke(msgs)

    iteration = (state.get("iteration") or 0) + 1
    usage = getattr(resp, "usage_metadata", None) or {}
    token_used = (state.get("token_used") or 0) + (usage.get("total_tokens") or 0)

    message_updates: List[Any] = [
        RemoveMessage(id=m.id, content="")
        for m in removed_history
        if getattr(m, "id", None)
    ]
    message_updates.append(resp)
    return {
        "messages": message_updates,
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
    searched_queries = set(state.get("searched_queries") or [])
    new_msgs: List[Any] = []

    for tc in tool_calls:
        name = tc.get("name", "")
        args = tc.get("args", {}) or {}
        fn = TOOL_MAP.get(name)
        started = time.perf_counter()
        status = "success"

        if name == create_note.name:
            decision = interrupt(
                {
                    "type": "approval_required",
                    "tool_call_id": tc.get("id", ""),
                    "tool_name": name,
                    "title": "创建知识库笔记",
                    "description": "Agent 请求执行写操作，确认后才会创建笔记。",
                    "args": args,
                    "preview": {
                        "title": str(args.get("title", ""))[:200],
                        "content": str(args.get("content", ""))[:500],
                        "folder_id": args.get("folder_id"),
                    },
                }
            )
            approved = bool(decision.get("approved")) if isinstance(decision, dict) else bool(decision)
            if not approved:
                status = "rejected"
                reason = decision.get("reason", "用户拒绝") if isinstance(decision, dict) else "用户拒绝"
                result = json.dumps({"status": "rejected", "reason": reason}, ensure_ascii=False)
            else:
                try:
                    result = _invoke_tool(fn, args, state)
                except Exception as e:  # noqa: BLE001
                    status = "error"
                    result = f"工具执行出错:{e}"
        else:
            if name == "search_notes":
                # 病灶B:同一轮内重复相同的检索词直接短路,防多跳检索死循环烧迭代。
                query = str((args or {}).get("query") or "").strip()
                if query and query in searched_queries:
                    result = json.dumps(
                        {
                            "error": "该检索词已在本轮执行过且结果已提供,请勿重复检索。"
                            "请基于已有结果直接作答,或换一个不同的检索词。"
                        },
                        ensure_ascii=False,
                    )
                    status = "error"
                else:
                    try:
                        result = _invoke_tool(fn, args, state) if fn else f"未知工具:{name}"
                        if not fn:
                            status = "error"
                    except Exception as e:  # noqa: BLE001
                        status = "error"
                        result = f"工具执行出错:{e}"
                    if query:
                        searched_queries.add(query)
            # 熔断:web_search 本轮已确认"永久未启用"后,后续请求直接短路,不再真调工具/烧 token。
            elif name == "web_search" and any(
                lg.get("tool") == "web_search" and "永久未启用" in (lg.get("result") or "")
                for lg in tool_log
            ):
                result = json.dumps(
                    {
                        "error": "web_search 已确认永久不可用(未配置 TAVILY_API_KEY),禁止再次调用。"
                        "请直接基于已有信息回答,或明确告知用户联网搜索未启用。"
                    },
                    ensure_ascii=False,
                )
                status = "error"
            else:
                try:
                    result = _invoke_tool(fn, args, state) if fn else f"未知工具:{name}"
                    if not fn:
                        status = "error"
                except Exception as e:  # noqa: BLE001
                    status = "error"
                    result = f"工具执行出错:{e}"

        latency_ms = max(0, int((time.perf_counter() - started) * 1000))
        if status == "success":
            try:
                parsed_result = json.loads(result)
                if isinstance(parsed_result, dict) and parsed_result.get("error"):
                    status = "error"
            except (TypeError, json.JSONDecodeError):
                pass

        new_msgs.append(ToolMessage(content=result, tool_call_id=tc.get("id", "")))
        thoughts.append({"type": "action", "content": f"{name}{json.dumps(args, ensure_ascii=False)}"})
        thoughts.append({"type": "observation", "content": result[:300]})
        tool_log.append(
            {
                "tool_call_id": tc.get("id", ""),
                "tool": name,
                "args": args,
                "result": result[:500],
                "latency_ms": latency_ms,
                "status": status,
            }
        )

        if name == "search_notes":
            try:
                docs = json.loads(result)
                if isinstance(docs, list):
                    documents.extend(docs)
            except Exception:
                pass

        if name == "get_note":
            # 病灶A:get_note 读到的完整内容并入 documents,保证 grade_documents/三查
            # 能看到 agent 实际读过的证据(与 P18 同理:snippet 截断会误判)。
            try:
                note = json.loads(result)
                if isinstance(note, dict) and note.get("id"):
                    doc = {
                        "id": note["id"],
                        "title": note.get("title") or "",
                        "snippet": (note.get("content") or "")[:300],
                        "full_content": note.get("content") or "",
                    }
                    for i, d in enumerate(documents):
                        if d.get("id") == note["id"]:
                            documents[i] = doc
                            break
                    else:
                        documents.append(doc)
            except Exception:
                pass

        if name == "web_search":
            # 联网结果同样作为证据进入 documents,供三查核对;失败结果(error dict)不收集。
            try:
                web_docs = json.loads(result)
                if isinstance(web_docs, list):
                    documents.extend(web_docs)
            except Exception:
                pass

    return {
        "messages": new_msgs,
        "thoughts": thoughts,
        "tool_calls_log": tool_log,
        "documents": documents,
        "searched_queries": sorted(searched_queries),
    }


def grade_documents(state: AgentState) -> Dict[str, Any]:
    docs = state.get("documents") or []
    thoughts = _append_thought(state, {"type": "check", "content": "grade_documents: 开始"})
    if not docs:
        thoughts.append({"type": "check", "content": "grade_documents: 无检索文档,放行"})
        return {"documents_grade": "yes", "thoughts": thoughts}

    provider = get_deepseek_provider()
    structured = provider.with_structured_output(GradeDocuments)
    resp = structured.invoke(
        [
            SystemMessage(content=GRADE_DOCUMENTS_PROMPT),
            HumanMessage(content=f"问题:{state['question']}\n\n文档:\n{_full_doc_text(docs)}"),
        ]
    )
    score = (resp.binary_score or "").lower()
    thoughts.append({"type": "check", "content": f"grade_documents: {score} ({resp.reason})"})
    return {"documents_grade": score, "thoughts": thoughts}


def _best_answer(messages: List[Any], turn_start_index: int = 0) -> str:
    """取本轮(自 turn_start_index 起)内容最长的 AIMessage 作为答案。
    (病灶B)rewrite/迭代循环后最后一条可能是退化短句,最长内容通常是最实质的答案;
    (M7.0 修复跨轮污染)限定本轮范围——checkpoint 保留近 24 条历史,若不限定,
    之前轮次的长答案会盖掉本轮较精炼的答案;多 agent 后 chat 冗长直答与知识答案同池,误选概率更大。
    带 tool_calls 的消息 content 多为空,已排除。"""
    start = max(0, int(turn_start_index or 0))
    best = ""
    for m in (messages or [])[start:]:
        if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None):
            content = m.content or ""
            if len(content) > len(best):
                best = content
    return best


def generate(state: AgentState) -> Dict[str, Any]:
    return {
        "answer": _best_answer(
            state.get("messages") or [], state.get("turn_start_index") or 0
        )
    }


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
        answer = _best_answer(
            state.get("messages") or [], state.get("turn_start_index") or 0
        )
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


# ---------- 意图识别 ----------
def intent_classify(state: AgentState) -> Dict[str, Any]:
    """意图识别节点。分类失败时 fail-safe 默认 knowledge，不让主流程被阻塞。"""
    question = state.get("question") or ""
    intent = "knowledge"
    reason = "fail-safe 默认走知识库检索"
    task_brief = ""  # M7.1:编排器任务简报,分类失败时留空(为空不注入)
    try:
        provider = get_deepseek_provider()
        structured = provider.with_structured_output(QueryIntent)
        resp = structured.invoke(
            [
                SystemMessage(content=INTENT_CLASSIFY_PROMPT),
                HumanMessage(content=question),
            ]
        )
        candidate = (getattr(resp, "intent", "") or "").strip().lower()
        if candidate in ("knowledge", "direct_answer", "web_search", "note_write"):
            intent = candidate
            reason = (getattr(resp, "reason", "") or "")[:120]
        else:
            reason = f"模型返回非法意图 {candidate!r},默认 knowledge"
        task_brief = (getattr(resp, "task_brief", "") or "").strip()[:200]
    except Exception as exc:  # noqa: BLE001 分类只是路由提示,失败不阻断
        reason = f"分类失败,默认 knowledge: {exc}"
    return {
        "intent": intent,
        # M7 A′:记录命中的子 Agent + 本轮起点(修复 _best_answer 跨轮污染:
        # 消息通道最后一条是本轮新问题,本轮答案只能从它之后产生)
        "current_agent": intent,
        "turn_start_index": max(0, len(state.get("messages") or []) - 1),
        # M7.1:编排器任务简报,为空不注入(防错误简报误导子 Agent)
        "task_brief": task_brief,
        "thoughts": _append_thought(state, {"type": "intent", "content": f"意图识别: {intent} | {reason}"}),
    }


def direct_answer(state: AgentState, *, store: BaseStore = None) -> Dict[str, Any]:
    """直答分支:通用常识/闲聊,跳过工具循环与三查,省 token 且避免简单题掉链。"""
    provider = get_deepseek_provider()
    system_prompt = DIRECT_ANSWER_PROMPT
    preference_context = get_preference_context(state.get("user_id", ""), store)
    if preference_context:
        system_prompt += "\n\n## 用户长期偏好\n" f"{preference_context}"
    question = state.get("question") or ""
    resp = provider.get_chat_model().invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ]
    )
    answer = (resp.content or "").strip() or "抱歉,我暂时无法回答这个问题。"
    return {
        # 同步写入 checkpoint,保证多轮会话上下文连续
        "messages": [HumanMessage(content=question), AIMessage(content=answer)],
        "answer": answer,
        "thoughts": _append_thought(
            state, {"type": "thought", "content": "direct_answer: 通用知识/闲聊,跳过检索直接作答"}
        ),
    }


def route_intent(state: AgentState) -> str:
    """条件边:按意图返回下一节点。direct_answer 走直答,其余走 agent_step。"""
    return "direct_answer" if (state.get("intent") == "direct_answer") else "agent_step"


# ---------- M7 A′ 多 Agent 路由 ----------
_INTENT_TO_AGENT = {
    "direct_answer": "chat_agent",
    "knowledge": "knowledge_agent",
    "web_search": "web_research_agent",
    "note_write": "note_write_agent",
}


def route_intent_multi(state: AgentState) -> str:
    """A′ 多 Agent 路由:意图 → agent 名。chat_agent 复用 direct_answer 节点,
    其余复用 agent_step 节点(策略由 AGENT_CONFIGS 查表决定);
    未知意图 fail-safe 回 knowledge_agent,与意图分类 fail-safe 同源。"""
    return _INTENT_TO_AGENT.get(state.get("intent") or "knowledge", "knowledge_agent")
