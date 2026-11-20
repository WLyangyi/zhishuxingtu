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
