from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from app.db.base import Base, TimestampMixin, generate_uuid


class AgentSession(Base, TimestampMixin):
    __tablename__ = "agent_sessions"
    __table_args__ = (Index("idx_agent_sessions_user_updated", "user_id", "updated_at"),)

    id = Column(String(36), primary_key=True, default=generate_uuid)  # = LangGraph thread_id
    user_id = Column(String(36), index=True)
    title = Column(String(500), default="新会话")
    # M7.4:本会话最近一轮命中的子 Agent 路由(knowledge/web_search/note_write/direct_answer,
    # 由 _stream_graph 从图终态回写;本地审计的 agent 维度,供路由准确率分析)
    agent_route = Column(String(32), default="")


class AgentToolCall(Base, TimestampMixin):
    __tablename__ = "agent_tool_calls"
    __table_args__ = (Index("idx_agent_tool_calls_session_created", "session_id", "created_at"),)

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), index=True)
    tool_name = Column(String(100))
    args_json = Column(Text)
    result_json = Column(Text)
    latency_ms = Column(Integer, default=0)
    status = Column(String(50), default="success")


class UserPreference(Base, TimestampMixin):
    """跨会话长期偏好；LangGraph Store 的持久化事实来源。"""

    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "preference_key", name="uq_user_preference_key"),
        Index("idx_user_preferences_user_updated", "user_id", "updated_at"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    preference_key = Column(String(100), nullable=False)
    preference_value = Column(Text, nullable=False)
