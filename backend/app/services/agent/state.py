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
    documents_grade: str
    hallucination_ok: str
    answer_ok: str
    intent: str
