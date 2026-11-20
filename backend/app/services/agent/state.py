from typing import Annotated, List, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """LangGraph Agent 状态(多轮会话靠 messages + checkpoint 记忆)。"""

    messages: Annotated[List[BaseMessage], add_messages]
    question: str
    session_id: str
    user_id: str
    iteration: int
    token_used: int
    documents: List[dict]
    answer: str
    thoughts: List[dict]
    tool_calls_log: List[dict]
    searched_queries: List[str]
    documents_grade: str
    hallucination_ok: str
    answer_ok: str
    intent: str
    # M7 A′ 多 Agent:命中哪个子 Agent(由 intent_classify 写入,chat/knowledge/web_research/note_write)
    current_agent: str
    # M7.1:编排器任务简报(为空不注入子 Agent system prompt)
    task_brief: str
    # 任务0.1:本轮起点问题的 message id,修复 _best_answer 裁剪后下标越界
    turn_start_id: str
    # 任务0.2:本轮开始时的 checkpoint_id,断流后用它作 config 重放
    turn_start_checkpoint_id: str
    # 任务1.1:意图锚点常驻字段(唯一真相,跨轮保留)
    core_intent: dict
    intent_version: int
    # 二期2.2:当前激活的 task id(锚点下沉 task);无 task 时 legacy 用 session_id 作锚点键
    current_task_id: str
    # 二期2.4:任务状态结构化常驻字段(跨轮保留,build_input 不重置,从 checkpoint 取)
    current_subtask: str
    completed_steps: List[str]
    context_snapshot: dict
    phase: str
    status: str
    # 任务1.1:本轮临时字段,build_input 每轮重置(双保险,防跨轮残留)
    # last_intent_change:本轮变更类型与来源,回写用
    last_intent_change: dict
    # low_confidence_hint:低置信拟变更提示,output 节点拼接到 answer 末尾
    low_confidence_hint: str
    # pending_preference:跨任务偏好 {key, value, scope},流中 upsert_preference
    pending_preference: dict
    # 二期2.4:待澄清问题(本轮需要用户澄清时写入,output 节点据此提问;build_input 每轮重置)
    pending_clarification: dict
